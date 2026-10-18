#!/bin/sh
echo "KERNEL $(uname -r)"
for m in sch_cake sch_netem sch_htb sch_fq_codel ifb cls_flower act_mirred sch_pie vcan; do
  if modprobe -n -v "$m" >/dev/null 2>&1; then echo "$m: OK"; else echo "$m: MISSING"; fi
done
for b in tc ip iperf3 nft iptables ethtool python3 go irtt nc; do
  if command -v "$b" >/dev/null 2>&1; then echo "$b: present"; else echo "$b: absent"; fi
done
# ---- testbed ----
for ns in lan rtr wan; do ip netns del $ns 2>/dev/null; done
ip netns add lan; ip netns add rtr; ip netns add wan
ip link add v-lan type veth peer name v-lanr
ip link add v-wanr type veth peer name v-wan
ip link set v-lan netns lan; ip link set v-lanr netns rtr; ip link set v-wanr netns rtr; ip link set v-wan netns wan
ip -n lan addr add 10.0.1.2/24 dev v-lan; ip -n rtr addr add 10.0.1.1/24 dev v-lanr
ip -n rtr addr add 10.0.2.1/24 dev v-wanr; ip -n wan addr add 10.0.2.2/24 dev v-wan
for ns in lan rtr wan; do ip -n $ns link set lo up; done
ip -n lan link set v-lan up; ip -n rtr link set v-lanr up; ip -n rtr link set v-wanr up; ip -n wan link set v-wan up
ip netns exec rtr sysctl -q -w net.ipv4.ip_forward=1
ip -n lan route add default via 10.0.1.1; ip -n wan route add default via 10.0.2.1
for p in "lan v-lan" "rtr v-lanr" "rtr v-wanr" "wan v-wan"; do set -- $p; ip netns exec $1 ethtool -K $2 tso off gso off gro off >/dev/null 2>&1; done
# WAN impairment: 20 Mbps, 20 ms each way, deep FIFO (1000 pkts) on WAN->router egress
ip netns exec wan tc qdisc add dev v-wan root netem delay 20ms rate 20mbit limit 1000
ip netns exec lan tc qdisc add dev v-lan root netem delay 20ms
echo "--- IDLE RTT ---"; ip netns exec lan ping -q -c 10 -i 0.2 10.0.2.2 | tail -1
cat > /tmp/srv.py <<'PY'
import socket,time
s=socket.socket(); s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1); s.bind(("0.0.0.0",5001)); s.listen(1)
c,_=s.accept(); b=b"\0"*65536; t=time.time()
try:
    while time.time()-t<22: c.sendall(b)
except Exception: pass
PY
cat > /tmp/cli.py <<'PY'
import socket,time,sys
s=socket.create_connection(("10.0.2.2",5001)); n=0; t=time.time()
while time.time()-t<18:
    d=s.recv(65536)
    if not d: break
    n+=len(d)
print("bulk Mbps %.1f"%(n*8/(time.time()-t)/1e6))
PY
run_load() {
  ip netns exec wan python3 /tmp/srv.py & SP=$!
  sleep 1
  ip netns exec lan python3 /tmp/cli.py & CP=$!
  sleep 4
  echo "--- RTT UNDER LOAD ($1) ---"; ip netns exec lan ping -q -c 40 -i 0.25 10.0.2.2 | tail -2
  wait $CP; kill $SP 2>/dev/null; wait $SP 2>/dev/null
  echo "--- qdisc stats WAN side ---"; ip netns exec wan tc -s qdisc show dev v-wan | grep -E "backlog|Sent" | head -2
}
run_load BASELINE_deepFIFO
# Optimized: router shapes downloads on LAN-side egress at 90% with HTB + fq_codel
ip netns exec rtr tc qdisc add dev v-lanr root handle 1: htb default 10
ip netns exec rtr tc class add dev v-lanr parent 1: classid 1:10 htb rate 18mbit ceil 18mbit
ip netns exec rtr tc qdisc add dev v-lanr parent 1:10 fq_codel
run_load OPTIMIZED_htb_fqcodel
echo "--- rtr qdisc ---"; ip netns exec rtr tc -s qdisc show dev v-lanr | grep -E "fq_codel|backlog|drop" | head -3
echo "--- CAKE attempt ---"; ip netns exec rtr tc qdisc replace dev v-wanr root cake bandwidth 18mbit 2>&1 | head -2
for ns in lan rtr wan; do ip netns del $ns; done
echo DONE
