import time, inspect, pybamm, numpy as np
pv = pybamm.ParameterValues("ECM_Example")
import pybamm.input.parameters.ecm.example_set as es
print("r0 signature:", inspect.signature(es.r0)); print("ocv signature:", inspect.signature(es.ocv))
src = inspect.getsource(es)
i = src.find("def r0"); print(src[i:i+700])
# scale to a 2.5 Ah 18650-like cell: capacity, thermal mass ~ 45 g * ~1000 J/kgK = 45 J/K
pv.update({"Cell capacity [A.h]": 2.5, "Nominal cell capacity [A.h]": 2.5, "Cell thermal mass [J/K]": 45,
           "Cell-jig heat transfer coefficient [W/K]": 0.1, "Jig thermal mass [J/K]": 1e6, "Jig-air heat transfer coefficient [W/K]": 100,
           "Lower voltage cut-off [V]": 2.5, "Current function [A]": 2.5, "RCR lookup limit [A]": 340})
# R0 in example set is per 100 Ah cell (~ mOhm); scale resistances x40 to get ~ tens of mOhm
R0 = pv["R0 [Ohm]"]; R1 = pv["R1 [Ohm]"]; C1 = pv["C1 [F]"]
pv.update({"R0 [Ohm]": lambda T,I,soc: 40*R0(T,I,soc), "R1 [Ohm]": lambda T,I,soc: 40*R1(T,I,soc), "C1 [F]": lambda T,I,soc: C1(T,I,soc)/40})
model = pybamm.equivalent_circuit.Thevenin()
exp = pybamm.Experiment(["Discharge at 10 A until 2.5 V", "Rest for 10 minutes", "Charge at 1.25 A until 4.2 V", "Hold at 4.2 V until 100 mA"])
sim = pybamm.Simulation(model, parameter_values=pv, experiment=exp)
t1=time.time(); pv.update({"Initial SoC": 0.98}); sim = pybamm.Simulation(model, parameter_values=pv, experiment=exp); sol = sim.solve(); t2=time.time()
print("solve s:", round(t2-t1,2))
T = sol["Cell temperature [degC]"].entries; V = sol["Voltage [V]"].entries; Q = sol["Throughput capacity [A.h]"].entries if "Throughput capacity [A.h]" in sol.all_models[0].variable_names() else np.array([0.0]); print([n for n in sol.all_models[0].variable_names() if "apacity" in n or "SoC" in n or "nergy" in n])
print("T min/max degC:", T.min().round(2), T.max().round(2), "| V min/max:", V.min().round(3), V.max().round(3), "| max discharge Ah:", Q.max().round(3))
print("total time h:", sol["Time [h]"].entries[-1].round(3))
print([n for n in sol.all_models[0].variable_names() if 'eat' in n][:10])
# second run timing (warm)
t3=time.time(); sol2 = pybamm.Simulation(model, parameter_values=pv, experiment=exp).solve(); print("warm solve s:", round(time.time()-t3,2))
