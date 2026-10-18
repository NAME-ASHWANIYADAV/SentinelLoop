# Local reproduction notes extracted verbatim from the adversarial reviewers' outputs (2026-10-18)

These are the reviewers' own words; the scripts they ran are in this folder (cmapss_baseline.py, wsl2_tc_testbed_check.sh, pybamm_ecm_smoke_test.py).

## Technical Skeptic (case 1, severity low)

The specialist's headline baseline REPRODUCES exactly, but on a different library version than stated. I re-ran scripts/baseline.py on FD001 from the locally downloaded NASA archive: unit-wise 5-fold CV RMSE all-rows/last-cycle = 14.18 / 2.48, official test last-cycle HGBR RMSE(capped)=14.22, RMSE(raw)=15.38, NASA score 314.0, RF 14.36, naive-mean 41.94, wall-clock 100 s. Environment was Python 3.12.1, scikit-learn 1.9.0, pandas 2.3.3 (specialist wrote 'scikit-learn 1.4.0'). File counts also verified locally: FD001 100/100 units, FD002 260/259, FD003 100/100, FD004 249 train units / 248 test units with 248-length RUL vector while readme.txt says 'Train 248, Test 249' - the swap the specialist flagged is real. [verified_fact]

Evidence: Local run of C:/Users/HP/AppData/Local/Temp/claude/C--Users-HP-OneDrive-Desktop-tata/f983720e-713e-4c7b-9ebb-a0f567283d43/scratchpad/scripts/baseline.py on dl/6. Turbofan Engine Degradation Simulation Data Set/inner/; pandas unit counts; readme.txt lines 19-21. data.nasa.gov page fetched live: 'License not specified', links CMAPSSData.zip, requests Saxena et al. PHM08 citation.

URLs: ['https://data.nasa.gov/dataset/cmapss-jet-engine-simulated-data', 'https://phm-datasets.s3.amazonaws.com/NASA/6.+Turbofan+Engine+Degradation+Simulation+Data+Set.zip']

## Technical Skeptic (case 1, severity medium)

Dependency and environment fragility is real but manageable: a pip --dry-run of 'mlflow>=3, evidently==0.7.23, streamlit, river, scikit-learn, pandas' resolved without conflict (142 packages: mlflow 3.17.1, evidently 0.7.23, streamlit 1.66.0, river 0.26.1, scikit-learn 1.9.1, plotly 5.24.1, pydantic 2.14.1) BUT it pulls pandas 3.0.6 and numpy 2.5.4, whereas the reproduced baseline ran on pandas 2.3.3; pandas 3 changes copy-on-write/string defaults and has not been exercised. On this very machine 'import streamlit' still fails (plotly 4.14.3: AttributeError Icicle) and mlflow is 2.15.1, confirming the specialist's warning. Evidently 0.7.23 (11 Sep 2026, Apache-2.0, Python>=3.10) verified. A lock file and a fresh-venv rehearsal are mandatory, not optional. [verified_fact]

Evidence: pip dry-run report dep_report.json in scratchpad; local import tests; PyPI evidently page.

URLs: ['https://pypi.org/project/evidently/', 'https://pypi.org/project/mlflow/']

## Technical Skeptic (case 3, severity low)

Independent reproduction of the headline latency claim on the team's own laptop: I built a 3-namespace testbed in this machine's WSL2 (kernel 6.6.87.2, WSL 2.6.1.0, 12 vCPU, 7.9 GB) with netem 'delay 20ms rate 20mbit limit 1000' on the WAN egress and a Python bulk TCP download. Idle RTT 40.2/44.4/82.2 ms (min/avg/max). Under load with a deep FIFO (baseline): RTT 253.9/638.0/3534.3 ms, netem backlog 674 packets, bulk 15.9 Mbps. After adding HTB (rate 18mbit) + fq_codel on the router's LAN-side egress: RTT 40.1/41.2/42.4 ms (mdev 0.49 ms), bulk 16.4 Mbps, WAN backlog 17 packets. That is a 93.5% reduction in mean RTT under load (98.8% in max) with bulk still at 82% of link - the specialist's '>=80% p95 reduction' target is conservative, and the 600 ms queueing arithmetic (1000 x 1500 B at 20 Mbps) matched the measured 638 ms mean. HTB printed 'quantum of class 10010 is big. Consider r2q change' as the specialist predicted. [verified_fact]

Evidence: scratchpad/wslcheck.sh run via wsl.exe -u root on 2026-10-18; tc -s qdisc output captured.

URLs: ['https://man7.org/linux/man-pages/man8/tc-netem.8.html', 'https://man7.org/linux/man-pages/man8/tc-htb.8.html', 'https://www.rfc-editor.org/rfc/rfc8290.html']

## Technical Skeptic (case 3, severity medium)

Kernel/tool availability on the team's machine confirmed, with gaps: modprobe -n shows sch_htb, sch_fq_codel, ifb, cls_flower, act_mirred present (netem demonstrably works), while sch_cake, sch_pie and vcan are MISSING; 'tc qdisc replace ... cake' fails with 'Specified qdisc kind is unknown'. The upstream config-wsl for linux-msft-wsl-6.6.y confirms '# CONFIG_NET_SCH_CAKE is not set' and '# CONFIG_NET_SCH_PIE is not set'. iperf3, nft, iptables, go and irtt are all absent (apt/go install needed; iproute2 6.1.0 and python3 present). For CI: the current ubuntu-24.04 runner image (20261012.334.1) runs kernel 6.17.0-1022-azure with passwordless sudo ('The Linux and macOS virtual machines both run using passwordless sudo'), iperf3 is NOT preinstalled, and packages.ubuntu.com shows sch_cake.ko only for 6.17 azure-fde and generic builds, not that exact -azure build, so the CAKE-in-CI comparison remains unconfirmed until one workflow runs. [verified_fact]

Evidence: Local modprobe/command checks; raw config-wsl fetch; runner-images readme; GitHub docs; packages.ubuntu.com contents search (noble, noble-updates).

URLs: ['https://raw.githubusercontent.com/microsoft/WSL2-Linux-Kernel/linux-msft-wsl-6.6.y/arch/x86/configs/config-wsl', 'https://github.com/actions/runner-images/blob/main/images/ubuntu/Ubuntu2404-Readme.md', 'https://docs.github.com/en/actions/reference/runners/github-hosted-runners', 'https://packages.ubuntu.com/search?searchon=contents&keywords=sch_cake.ko&mode=filename&suite=noble-updates&arch=amd64']

## Technical Skeptic (case 3, severity medium)

WSL2 timing noise threatens the 'adaptation speed and policy stability' criterion more than the specialist allows: on an idle 40 ms emulated path I measured max RTT 82 ms with mdev 12.6 ms over 10 pings (a 40 ms spike with nothing else running). The proposed AIMD estimator rule 'RTT delta > 25 ms for 3 samples -> rate *= 0.85' would false-trigger on such VM scheduling spikes, producing exactly the rate flips the rubric penalises, and the ground-truth estimator error target (<=15%) could be missed for reasons unrelated to the algorithm. Mitigations are known (median-of-N probes, longer refractory, running the headline runs in a native Ubuntu VM or CI rather than WSL) but they cost tuning time the team has not budgeted. Netem's man page also warns 'Combining netem with other qdisc is possible but may not always work' and that rate emulation is 'impacted by ... kernel clock granularity' producing bursts. [verified_fact for measurements and man page; technical_inference for the estimator impact]

Evidence: Idle ping line from my run: 'rtt min/avg/max/mdev = 40.160/44.375/82.201/12.608 ms'; tc-netem(8) LIMITATIONS text.

URLs: ['https://man7.org/linux/man-pages/man8/tc-netem.8.html', 'https://arxiv.org/abs/2208.05862']

## Technical Skeptic (case 3, severity low)

Reference-design provenance holds up: cake-autorate (GPL-2.0, bash, 1,316 commits, 573 stars, stable 3.2.1) estimates capacity from load plus OWD/RTT to reflectors with a refractory period and min/base/max clamps, and is CAKE-specific, so the team's Python re-implementation against HTB is new code with attribution, not a copy. irtt is 0.9.2 (GPL-2.0), needs Go to build from source, but an 'irtt' package exists in Ubuntu noble. The CAKE paper (arXiv 1804.07617, CC BY-SA 4.0) exists; the specific 200 ms vs 50-500 ms numbers the specialist quoted are from the body, which I did not re-read. [verified_fact]

Evidence: GitHub pages fetched; packages.ubuntu.com search for irtt returned 'Package irtt' in noble.

URLs: ['https://github.com/lynxthecat/cake-autorate', 'https://github.com/heistp/irtt', 'https://arxiv.org/abs/1804.07617']

## Technical Skeptic (case 5, severity medium)

Not in my brief to investigate deeply, but for ranking: Case 5's credibility on 'Edge Performance' depends entirely on ARM hardware the team is not known to have, and its tokens/s inputs are community Ollama blog numbers; nothing in the specialist's output was reproduced locally. Combined with being the most LLM-trendy case (largest expected entrant pool), its variance is the highest of the five. [technical_inference]

Evidence: Specialist 5's own 'critical' risk entry and 'unverified_assumption' labels on all Pi throughput sources.

URLs: ['https://www.raspberrypi.com/documentation/accessories/ai-hat-plus.html']

## Competition Strategist (case 1, severity high)

The specialist's load-bearing local numbers reproduce. I re-ran scripts/baseline.py on FD001 with python -I: unit-wise 5-fold CV RMSE all-rows/last-cycle = 14.18 / 2.48; official test last-cycle HGBR RMSE 14.22 (capped truth), 15.38 (raw truth), NASA score 314.0, n=100; RF 14.36 / 338.4; naive mean-RUL 41.94. The 'how we could have cheated' slide (2.48 vs 14.22) is therefore verified, not asserted. Caveats: elapsed 156 s vs the claimed 94-352 s band (within band), and a joblib/_winapi.CreateProcess traceback appeared during the RandomForest n_jobs=-1 step on this Windows box, confirming the environment-fragility warning. verified_fact.

Evidence: Local re-run 2026-10-18 of C:/Users/HP/AppData/Local/Temp/claude/C--Users-HP-OneDrive-Desktop-tata/f983720e-713e-4c7b-9ebb-a0f567283d43/scratchpad/scripts/baseline.py against dl_cmapss/.../inner; dataset files train/test/RUL_FD001-FD004 present on disk.

URLs: ['https://phm-datasets.s3.amazonaws.com/NASA/6.+Turbofan+Engine+Degradation+Simulation+Data+Set.zip']

## Competition Strategist (case 1, severity medium)

The recommended ML differentiator (GBM + conformal intervals across all four subsets) is itself already published: Robinson, IJPHM vol 17 no 1 (27 Apr 2026) uses a gradient boosting regressor + asymmetric CQR on all four C-MAPSS subsets, test RMSE 13.26-16.85, coverage 88-92% at 90% nominal. The team's novelty therefore lies only at the integration layer (interval lower bound -> triage severity, drift -> gated retraining, leakage-audited protocol); it must cite Robinson and position itself as 'operationalising' it, or a well-read judge will call the ML a reproduction. verified_fact.

Evidence: Fetched https://www.papers.phmsociety.org/index.php/ijphm/article/view/4724 (title, author, abstract confirm GBM + CQR, RMSE 13.26-16.85, coverage 88-92%).

URLs: ['https://www.papers.phmsociety.org/index.php/ijphm/article/view/4724']

## Competition Strategist (case 3, severity high)

Solution-space crowding is at the primitive level, not the system level. GitHub topic 'traffic-shaping' has 94 repos (tcconfig 854 stars, LibreQoS 723, sqm-scripts 288, TrafficToll 260) and 'qos' has 278 (LibreQoS, go-tc 532); cake-autorate (GPL-2.0, 573 stars, 1,316 commits) already implements the latency-feedback rate controller the specialist proposes to re-implement. No repo found is an intent-aware, self-verifying home QoS controller with classification confidence, rollback and a dashboard. So the differentiator (verify-or-rollback + ground-truth-scored estimator + CI-reproduced experiments) is open, but a broadband-vertical judge will know that SQM/CAKE/cake-autorate deliver most of the latency win for free; the team must frame itself as the verification/intent layer above them. verified_fact.

Evidence: Fetched https://github.com/topics/traffic-shaping (94), https://github.com/topics/qos (278), https://github.com/lynxthecat/cake-autorate (GPL-2.0, 573 stars, pings reflectors, adjusts CAKE rates).

URLs: ['https://github.com/topics/traffic-shaping', 'https://github.com/topics/qos', 'https://github.com/lynxthecat/cake-autorate']

## Competition Strategist (case 3, severity medium)

The specialist's environment claim stands on this machine: WSL 2.6.1.0, kernel 6.6.87.2-microsoft-standard-WSL2; modprobe -n: sch_htb OK, sch_fq_codel OK, sch_netem OK, cls_flower OK, ifb OK, sch_cake MISSING. The HTB+fq_codel testbed is demoable on the team's Windows laptop; the CAKE reference comparison is not without a VM/CI. Judge-visible evidence is the strongest among the unweighted cases because the PDF itself mandates 'Automated baseline-versus-optimized experiments' and a scripted demonstration that resets, impairs, collects evidence and generates a report, i.e. the evidence format is prescribed. verified_fact + source_derived_requirement.

Evidence: Local wsl.exe modprobe check 2026-10-18; cs3.md lines 31-40 (Expected Output and Acceptance Evidence).

URLs: ['https://raw.githubusercontent.com/microsoft/WSL2-Linux-Kernel/linux-msft-wsl-6.6.y/arch/x86/configs/config-wsl']

## Competition Strategist (case 2, severity medium)

The PyBaMM timing evidence is real but the experiment did not run as described. My re-run of ecm_test2.py with the specialist's venv (PyBaMM 26.10.1.0): cold solve 0.24 s, warm 0.13 s, T 25.0-47.69 C, V 2.907-3.945 V, total simulated time 0.245 h. A 10 A discharge of a 2.5 Ah cell is ~0.25 h, so only the discharge step executed; the 'Rest / Charge at 1.25 A until 4.2 V / Hold at 4.2 V' steps never ran (V never reached 4.2 V and total time is not ~2 h). The specialist's demo plan validates charge time against the datasheet (136 min standard / 55 min rapid) using this path, which is therefore unproven. Sub-second cost is still credible; the charge-step termination must be debugged before it is a demo claim. verified_fact (timing) / unverified_assumption (charge validation).

Evidence: Local re-run 2026-10-18 of scratchpad/ecm_test2.py via pyb_env/Scripts/python.exe; output lines 'solve s: 0.24', 'total time h: 0.245', 'warm solve s: 0.13'.

URLs: ['https://pypi.org/project/pybamm/']
