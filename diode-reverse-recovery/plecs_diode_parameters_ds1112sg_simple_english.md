# DS1112SG60 diode stack at 13.8 kV: how the PLECS and Simscape diode parameters are obtained from the datasheet

**Plain-English version of the calculation note "Parametri PLECS e Simscape del DS1112SG60", Rev. 01, 2026-10-01, Secom Proposal Engineering, D. Bagnara.**

The original Italian note is kept next to this file: [`original/plecs_diode_parameters_ds1112sg.pdf`](original/plecs_diode_parameters_ds1112sg.pdf). This version keeps every number, formula, table and conclusion of the original. Only the words are simpler. Where a sentence of the original packs several ideas together, it is split into short sentences here. Nothing new is added; a few short "in other words" remarks are marked as such.

If the physics behind chapter 5 (stored charge, lifetime, why the recovery looks the way it does) is the hard part, read the companion document [`physics_of_reverse_recovery.md`](physics_of_reverse_recovery.md) first or alongside.

---

## Revision history of the original note

| Rev. | Date | Author | Description |
|---|---|---|---|
| 00 | 2026-10-01 | D. Bagnara | First issue. How the ten parameters of the PLECS initialisation block are derived from the datasheet DS4181-5.0 and from the Dynex application note AN6531. Operating point of the B6 bridge at 13.8 kV, 60 A. |
| 01 | 2026-10-01 | D. Bagnara | Added section 7: the same data converted into the parameters of the charge-controlled diode (Lauritzen–Ma) of the MATLAB/Simscape model (`diode_lm_params.m`), a table of the twelve Dynex/Infineon sets, and a check on the test circuit. |

## Contents

1. [Goal and result](#1-goal-and-result)
2. [The PLECS model and what it asks for](#2-the-plecs-model-and-what-it-asks-for)
3. [Operating point of the circuit: I_F0 and dI_r/dt](#3-operating-point-of-the-circuit-i_f0-and-di_rdt)
4. [Static parameters](#4-static-parameters)
   4.1 V_RRM · 4.2 V_f0 and r_t · 4.3 R_off · 4.4 C_j
5. [Recovery parameters](#5-recovery-parameters)
   5.1 The rated point and Fig. 4 of the datasheet · 5.2 Why Q_rr at the operating point cannot be read, and how it is extrapolated · 5.3 I_rrm and t_rr from the triangle · 5.4 Q_rr unbalance between the diodes
6. [Checks on the model](#6-checks-on-the-model)
7. [Mapping onto the Simscape charge-controlled model (Lauritzen–Ma)](#7-mapping-onto-the-simscape-charge-controlled-model-lauritzenma)
   7.1 The equations of the block · 7.2 From the ramp to the peak and to the tail · 7.3 Inversion · 7.4 Conduction · 7.5 The other parameters · 7.6 The twelve sets · 7.7 Check · 7.8 Listing of `diode_lm_params.m`
8. [Data to ask Dynex for](#8-data-to-ask-dynex-for)

[References](#references)

## Symbols used in this note

| Symbol | Meaning |
|---|---|
| $I_{F0}$, `If0_ref` | forward current of the diode just before it turns off (the reference current of the model) |
| $a = \mathrm{d}I_r/\mathrm{d}t$, `di_dt_ref` | slope of the diode current while it is falling to zero, forced by the circuit (A/s) |
| $Q_{rr}$ | reverse recovery charge: the area under the negative part of the current (C) |
| $I_{rrm}$ | peak of the reverse current (A) |
| $t_{rr}$ | reverse recovery time (s) |
| $t_a$, $t_b$ | time from the zero crossing to the peak, and from the peak back to zero; $t_{rr} = t_a + t_b$ |
| $s = t_b/t_a$ | softness factor |
| $\tau$ | carrier lifetime (s) |
| $T_M$ | transit time of the charge-controlled model (s) |
| $V_{RRM}$ | repetitive peak reverse voltage rating |
| $V_{TO}$, $r_T$ | threshold voltage and slope resistance of the forward characteristic (datasheet) |
| $V_{f0}$, $r_t$ | the same two numbers as the PLECS parameters `Vf0`, `rt` |
| $R_{off}$ | resistance of the model when the diode is blocking |
| $C_j$ | junction capacitance |
| $T_{vj}$, $T_j$ | junction temperature |
| $n = 6$ | number of diodes in series in one stack |
| $C_{sn}$, $R_{sn}$ | snubber capacitor and resistor across each diode |
| $R_b$ | static balancing resistor across each diode |
| $L_c$ | commutation inductance on each AC phase |
| $u$, `Max_Qrr_unbalance` | relative spread of $Q_{rr}$ between the diodes of a stack |

---

## 1 Goal and result

The PLECS model of the rectifier (`mv_dstack_six_pulse_rectifier.plecs`) uses the component *Diode with Reverse Recovery* for every diode of the stack. Its parameters are set in the initialisation script.

This note shows, one parameter at a time, how the values of the block below come from three sources:

- the Dynex DS1112SG datasheet (DS4181-5.0) [1];
- the Dynex application note AN6531 [2];
- the operating point of the circuit.

It also says, for each value, whether it is read directly from the datasheet, extrapolated from it, or only estimated.

Section 7 then shows how the same data become the physical parameters ($\tau$, $T_M$, $I_s$, $R_s$) of the charge-controlled diode used in the MATLAB/Simscape twin model. It also checks that the two models recover the same charge with the same peak current.

```matlab
Vrrm=6000;          %V   - DS1112SG60 (VRSM 6100)
roff=1.2e6;         %Ohm - 3253 V / 2.7 mA at Tj=100 C, law 0.96
                    %      (2.1e6 with the Dynex curves; 8e4 at VRRM and 150 C)
Cj=5e-10;           %F   - estimate, not in the datasheet
Vf0=0.9;            %V   - VTO max at 150 C
rt=0.93e-3;         %Ohm - rT max at 150 C
If0_ref=60;         %A
di_dt_ref=1.07e5;   %A/s - V0/(2Lc)
Qrr_ref=0.45e-3;    %As - middle value at 100 C (floor 0.32e-3 / 7.0 A / 92 us;
                    %      worst 1.2e-3 / 13.4 A / 176 us)
Irrm_ref=8.3;       %A
Trr_ref=2*Qrr_ref/Irrm_ref; %s - 109 us
```

Table 1 says where each value comes from. Three parameters are read directly from the datasheet ($V_{RRM}$, $V_{TO}$, $r_T$). Two come from the circuit ($I_{F0}$, $\mathrm{d}I_r/\mathrm{d}t$). Three are extrapolations of the datasheet to the operating point ($R_{off}$, $Q_{rr}$, $I_{rrm}$; $t_{rr}$ follows from them). One is an estimate ($C_j$).

**Table 1: where the parameters of the PLECS block come from.**

| Parameter | Value | Origin | Type |
|---|---|---|---|
| `Vrrm` | 6000 V | *Voltage ratings* table, grade SG60 | datasheet value |
| `Vf0` | 0.9 V | $V_{TO}$ max at $T_{vj}$ = 150 °C | datasheet value |
| `rt` | 0.93 mΩ | $r_T$ max at $T_{vj}$ = 150 °C | datasheet value |
| `roff` | 1.2 MΩ | $I_{RM}$ = 75 mA at $V_{RRM}$, 150 °C, moved to 3253 V, 100 °C | extrapolation (§4.3) |
| `Cj` | 0.5 nF | not in the datasheet; estimated depletion capacitance | estimate (§4.4) |
| `If0_ref` | 60 A | DC current of the bridge | circuit (§3) |
| `di_dt_ref` | 1.07 × 10⁵ A/s | $V_0/(2L_c)$ at the end of the commutation | circuit (§3) |
| `Qrr_ref` | 0.45 mC | $Q_S$ of datasheet Fig. 4 extrapolated to 0.107 A/µs and 100 °C | extrapolation (§5.2) |
| `Irrm_ref` | 8.3 A | from the recovery triangle with $Q_{rr}$, $\mathrm{d}I_r/\mathrm{d}t$ and softness 0.4 | derived (§5.3) |
| `Trr_ref` | 109 µs | $2Q_{rr}/I_{rrm}$ | derived (§5.3) |

---

## 2 The PLECS model and what it asks for

The PLECS component *Diode with Reverse Recovery* [3] is an ideal diode made of straight pieces ($V_f$, $R_{on}$, $R_{off}$). On top of it, a small behavioural network adds the reverse recovery:

- a small measuring inductance $L_{rr}$;
- a resistor;
- a current source, driven linearly by the voltage across $L_{rr}$. That voltage is proportional to the slope $\mathrm{d}i/\mathrm{d}t$ of the diode current.

The recovery parameters are:

- the reference operating point, $I_{F0}$ and $\mathrm{d}I_r/\mathrm{d}t$;
- three sizes of the recovery triangle: $t_{rr}$, $I_{rrm}$ and $Q_{rr}$.

Only two of the three triangle sizes are independent. If you give all three, PLECS ignores $Q_{rr}$ and uses $t_{rr}$ and $I_{rrm}$, with $Q_{rr} = \tfrac{1}{2} I_{rrm} t_{rr}$.

Two practical consequences decide which values to write.

1. **The model scales with the real $\mathrm{d}i/\mathrm{d}t$.** The current source is proportional to $L_{rr}\,\mathrm{d}i/\mathrm{d}t$. So the recovery current produced in the circuit is roughly

   $$I_{rrm} \cdot \frac{(\mathrm{d}i/\mathrm{d}t)_{\text{circuit}}}{(\mathrm{d}I_r/\mathrm{d}t)_{\text{parameter}}}.$$

   Take the numbers of a datasheet measured at 10 A/µs and put them in a circuit that runs at 0.1 A/µs. The model then extrapolates over two decades. It produces a recovery one hundred times smaller than the nominal one, and nothing warns you. This is why the parameters must be given *at the operating point of the circuit*: $\mathrm{d}I_r/\mathrm{d}t$ equal to the real slope, and $I_{F0}$ equal to the real current. Then the scaling ratio is one, and the simulated recovery is exactly what is written in the parameters.

2. **Geometric constraint $I_{rrm} < t_{rr}\,\mathrm{d}I_r/\mathrm{d}t$.** The current reaches its peak along the ramp, after $t_a = I_{rrm}/(\mathrm{d}I_r/\mathrm{d}t)$. The peak must fall inside $t_{rr}$ (Fig. 1). If the condition is not met, the script stops with the message *Parameters for reverse recovery must satisfy: Irrm < trr \* dIr/dt*.

**Figure 1 (described).** The recovery triangle used by PLECS. The current $i_D$ starts at $I_F$ and falls with the slope $-\mathrm{d}I_r/\mathrm{d}t$ forced by the circuit. It crosses zero at $t_0$. It keeps falling with the same slope and reaches $-I_{rrm}$ after $t_a = I_{rrm}/(\mathrm{d}I_r/\mathrm{d}t)$. Then it goes back to zero in a straight line, in a time $t_b$. The whole recovery lasts $t_{rr} = t_a + t_b$. The grey triangle under the zero line has area $Q_{rr} = \tfrac{1}{2} I_{rrm} t_{rr}$. The ratio $s = t_b/t_a$ is the softness factor. From $Q_{rr} = \tfrac{1}{2} I_{rrm} t_{rr}$ and $t_{rr} = (1+s)\,t_a$ it follows that

$$I_{rrm} = \sqrt{\frac{2\,Q_{rr}\,(\mathrm{d}I_r/\mathrm{d}t)}{1+s}}.$$

> The same triangle, drawn next to the charge-controlled waveform, is [figure 2 of the physics document](figures/fig2_recovery_waveform.svg).

---

## 3 Operating point of the circuit: I_F0 and dI_r/dt

In the B6 bridge with an inductive load, each diode conducts for 120°. It turns off at the end of the commutation with the diode of the next phase. During the commutation, the current of the outgoing diode falls with a slope set by the instantaneous line-to-line voltage applied to the two commutation inductances in series, $2L_c$.

Let $\hat V = \sqrt{2}\,V_{LL}$ be the peak line-to-line voltage, $\omega = 2\pi f$ and $I_d$ the DC current. The overlap angle $\mu$, the commutation voltage $V_0$ at the end of the overlap, and the slope at the zero crossing of the current are:

$$\cos\mu = 1 - \frac{2\,\omega L_c I_d}{\hat V}, \qquad V_0 = \hat V \sin\mu, \qquad \left.\frac{\mathrm{d}i}{\mathrm{d}t}\right|_{i=0} = \frac{V_0}{2L_c}. \tag{3.1}$$

With the data of the script ($V_{LL}$ = 13.8 kV, $f$ = 50 Hz, $I_d$ = 60 A, $L_c = L_{line}$ = 31.1 mH, which is a 1.1 MVA transformer with $u_k$ = 6 %):

$$\hat V = 19.52\ \text{kV}, \quad \mu = 20.0°, \quad V_0 = 6.66\ \text{kV}, \quad \frac{\mathrm{d}i}{\mathrm{d}t} = \frac{6660}{2 \times 0.0311} = 1.07 \times 10^5\ \text{A/s} = 0.107\ \text{A/µs}.$$

This is `di_dt_ref`.

The ramp lasts $I_d/(\mathrm{d}i/\mathrm{d}t)$ = 560 µs. That is much longer than the carrier lifetime (30–100 µs). So this is a *long ramp*. This fact decides how $Q_{rr}$ is extrapolated (§5.2).

`If0_ref` is the real forward current, 60 A, not the 1000 A of the datasheet. In the long-ramp regime the charge left at the zero crossing does not depend on $I_F$. So the model must not rescale anything with respect to the reference current.

With the 1.25 MVA transformer ($L_c$ = 29 mH) the slope is 0.114 A/µs; with $u_k$ = 4 % it is 0.14 A/µs. The slope must be recalculated if the transformer changes.

---

## 4 Static parameters

### 4.1 V_RRM

The datasheet lists voltage grades from SG55 (5500 V) to SG60 (6000 V), with $V_{RSM} = V_{RRM} + 100$ V. The design assumes grade SG60, which must be written in full in the order: `Vrrm = 6000`.

In PLECS this value is only a reference. The ideal diode does not break. So the check of the peak voltage on the first diode against $0.8\,V_{RRM}$ = 4800 V must be done afterwards on the waveforms.

### 4.2 V_f0 and r_t

The forward characteristic is given as a threshold plus a slope: $v_F = V_{TO} + r_T\, i_F$, with $V_{TO} \le 0.9$ V and $r_T \le 0.93$ mΩ at $T_{vj}$ = 150 °C. So `Vf0 = 0.9`, `rt = 0.93e-3`.

This threshold model is fitted for currents of hundreds of amperes. At 60 A it overestimates the voltage drop (the equation of datasheet Fig. 2, valid from 500 A, would give about 0.9 V in total at 60 A and 125 °C). So the forward loss

$$P_F = V_{TO}\, I_{F(AV)} + r_T\, I_{F(RMS)}^2 = 0.9 \times 21 + 0.93 \times 10^{-3} \times 33^2 = 19.9\ \text{W}$$

is conservative. For the sizing of the stack, $V_{f0}$ and $r_t$ matter little. They set the losses in the diodes and the voltage at which the level is clamped during conduction.

### 4.3 R_off: from the rated reverse current to the operating point

The datasheet gives one number only: $I_{RM} \le 75$ mA at $V_{RRM}$ and $T_{case}$ = 150 °C. That is $R_{off} = 6000/0.075 = 80$ kΩ at the test point. It is a production test limit, not the value at the operating point, where both voltage and temperature are lower.

There are no curves for the DS1112SG. So the general curves of application note AN6531 [2] are used (its Fig. 4, taken from AN6161). The manufacturer itself calls them approximate.

- **Voltage:** $I_R(V)/I_R(V_{RRM}) \approx 0.30$ at 54 % of the rated voltage. The peak voltage per level is $\hat V/6$ = 3253 V, which is 54 % of 6000 V.
- **Temperature:** the curve, normalised at 125 °C, is about 0.30 at 100 °C, 1.0 at 125 °C, 2.7 at 140 °C. Extending it with the same exponential trend (doubling every ≈ 13 K) gives ≈ 4.2 at 150 °C, which is the temperature of the datasheet value. So the factor between 150 and 100 °C is $0.30/4.2 = 0.07$.

As an alternative, one can use the law that Infineon gives for the D711N65T, $0.96^{(T_{vj,max} - T_j)}$, which doubles every 17 K. Between 150 and 100 °C it gives 0.13. It is less steep, so more conservative. Table 2 gives the reverse current of a device at the limit, and the corresponding $R_{off}$, with the two laws.

The value written in the script, `roff = 1.2e6`, is the one of the $0.96^{\Delta T}$ law at $T_j$ = 100 °C. It is the more conservative of the two at that temperature.

In the model, $R_{off}$ acts only on the static voltage sharing (in parallel with $R_b$) and on the reverse losses. To simulate the leakage unbalance, the "best" diode gets a very high $R_{off}$ (20–30 MΩ) and the other five get the value of the table. A typical device leaks three to ten times less than the limit.

**Table 2: reverse current of a device at the limit ($I_{RM}$ = 75 mA at 6000 V, 150 °C), moved to 3253 V, and $R_{off} = 3253/I_R$.**

| $T_j$ | $I_R$, Dynex curves | $R_{off}$ | $I_R$, law $0.96^{\Delta T}$ | $R_{off}$ |
|---|---|---|---|---|
| 70 °C | 0.53 mA | 6.1 MΩ | 0.80 mA | 4.1 MΩ |
| 85 °C | 0.80 mA | 4.1 MΩ | 1.48 mA | 2.2 MΩ |
| 100 °C | 1.53 mA | 2.1 MΩ | 2.73 mA | 1.2 MΩ |
| 110 °C | 2.62 mA | 1.2 MΩ | 4.10 mA | 0.8 MΩ |
| 125 °C | 5.87 mA | 0.55 MΩ | 7.57 mA | 0.43 MΩ |
| 150 °C | 22.5 mA | 0.14 MΩ | 21 mA | 0.15 MΩ |

### 4.4 C_j

The datasheet does not give the junction capacitance. It is estimated as the depletion capacitance of a wafer of 40 mm diameter ($A \approx 1.3 \times 10^{-3}$ m²) with a depleted zone of 0.3–0.5 mm at 3 kV:

$$C_j = \frac{\varepsilon_{Si}\, A}{w} \approx 0.3\text{–}0.5\ \text{nF}, \qquad \text{so } C_j = \text{5e-10}.$$

This is 0.5 % of $C_{sn}$ = 100 nF. It does not affect the voltage sharing or the losses. Its only job is to give the ideal diode a finite capacitance, for the numerical stability of the fast edges (corner frequency $1/(2\pi R_{sn} C_j) \approx 1.4$ MHz).

---

## 5 Recovery parameters

### 5.1 The rated point and Fig. 4 of the datasheet

The datasheet characterises the recovery at one point only:

- $Q_S$ = 3000 µC and $I_{rr}$ = 90 A,
- at $I_F$ = 1000 A, $\mathrm{d}I_{RR}/\mathrm{d}t$ = 3 A/µs, $T_{case}$ = 150 °C, $V_R$ = 100 V.

Fig. 4 of the datasheet extends $Q_S$ as a function of the slope, from about 0.7 A/µs (≈ 2100 µC) to 60 A/µs (≈ 6500 µC). On a log-log plot it is a straight line with slope

$$Q_S \propto \left(\frac{\mathrm{d}i}{\mathrm{d}t}\right)^{0.28}, \qquad \frac{\log(6500/3000)}{\log(50/3)} \approx 0.28. \tag{5.1}$$

> In other words: the charge grows with the slope, but much more slowly than in proportion. Ten times the slope gives only about twice the charge.

There is no curve of $I_{rr}$. It is rebuilt from the triangle (§5.3). At the rated point: $t_a = 90/3 = 30$ µs, $t_{rr} = 2 \times 3000/90 = 67$ µs, so $t_b$ = 37 µs and softness $s = t_b/t_a = 1.2$.

### 5.2 Why Q_rr at the operating point cannot be read, and how it is extrapolated

Our circuit works at 0.107 A/µs, seven times below the last published point. The physics of the long ramp says how to extrapolate.

The stored charge $q$ obeys

$$\frac{\mathrm{d}q}{\mathrm{d}t} = i - \frac{q}{\tau},$$

where $\tau$ is the carrier lifetime. For a ramp $i = I_F - a\,t$ that lasts much longer than $\tau$, the charge follows the current with a constant delay: $q \approx \tau\, i(t) + a\tau^2$. At the zero crossing of the current there is still

$$q(t_0) \approx a\,\tau^2, \tag{5.2}$$

which does not depend on $I_F$ and is linear in the slope $a$.

> In other words: the charge inside the diode cannot follow the current instantly. It lags behind by one lifetime. When the current reaches zero, the charge is still what the current had one lifetime earlier, $a\tau$, multiplied by $\tau$. The physics document explains this step in detail.

From the rated point one gets an *apparent* lifetime $\tau = \sqrt{Q_S/a} = \sqrt{3 \times 10^{-3} / 3 \times 10^{6}} = 32$ µs at 3 A/µs, and 55 µs at 0.7 A/µs. The apparent lifetime grows as the slope decreases. The reason: at high $\mathrm{d}i/\mathrm{d}t$ a part of the charge recombines during the recovery and is never measured at the terminals. When the ramp becomes long, the apparent lifetime saturates towards the true lifetime of the wafer (50–100 µs for a 6 kV diode of this size).

Two extrapolations therefore bracket the value at 0.107 A/µs (Fig. 2):

- **floor:** linear scaling (5.2) from the last published point, with $\tau$ held at 55 µs: $Q_{rr} = 2100 \times 0.107/0.7 = 320$ µC;
- **ceiling:** continuation of the straight line of Fig. 4 with slope 0.28: $Q_{rr} = 3000 \times (0.107/3)^{0.28} = 1180$ µC, which corresponds to $\tau \approx 105$ µs.

Both are at $T_{vj}$ = 150 °C. The charge scales with the lifetime, and the lifetime grows about linearly with the absolute temperature. So $Q_{rr} \propto T_j^2$. Between 150 and 100 °C the factor is $(373/423)^2 = 0.78$.

The value chosen for the script, `Qrr_ref = 0.45e-3`, is the geometric mean of the two extremes ($\sqrt{320 \times 1180} = 615$ µC at 150 °C), moved to 100 °C: $615 \times 0.78 \approx 480$ µC, rounded to 450 µC. The rounding keeps it consistent with set "D" of the charge-controlled model of the earlier notes (0.59 mC at $T_{vj}$ max). It is a defensible middle point, not a measured value. The true value at 0.1 A/µs can only come from Dynex (§8).

**Figure 2 (described).** Stored charge of the DS1112SG against the slope of the current, on a log-log plot. The datasheet curve at $T_{vj}$ max is a straight line ($\propto a^{0.28}$) through the rated point (3 A/µs) and the last published point (0.7 A/µs). Below 0.7 A/µs two lines go down to the operating point (0.107 A/µs, dotted vertical line): the continuation of the straight line (ceiling) and the linear scaling $a\tau^2$ (floor). At the operating point the figure also marks the geometric mean at 150 °C and the value chosen at 100 °C.

> The same plot, rebuilt from the numbers of this note, is [figure 5 of the physics document](figures/fig5_qs_vs_didt.svg).

### 5.3 I_rrm and t_rr from the triangle

Once $Q_{rr}$ and the slope $a = \mathrm{d}I_r/\mathrm{d}t$ are fixed, the triangle of Fig. 1 ties the other two sizes to the softness $s = t_b/t_a$:

$$I_{rrm} = \sqrt{\frac{2\,a\,Q_{rr}}{1+s}}, \qquad t_{rr} = \frac{2 Q_{rr}}{I_{rrm}}, \qquad t_a = \frac{I_{rrm}}{a} < t_{rr}\ \text{(PLECS constraint)}. \tag{5.3}$$

At the rated point $s$ = 1.2. With a long ramp the tail becomes shorter than the rise. The leftover charge is small, and almost all of it is extracted before the peak. (In the Lauritzen–Ma model the rise lasts $\tau - t_{tail}$ and the tail 2–3 $t_{tail}$, with $t_{tail} \approx 15$–25 µs, that is $s \approx 0.3$–0.5.) The value $s = 0.4$ is adopted:

$$I_{rrm} = \sqrt{\frac{2 \times 1.07 \times 10^5 \times 0.45 \times 10^{-3}}{1.4}} = 8.3\ \text{A}, \qquad t_{rr} = \frac{2 \times 0.45 \times 10^{-3}}{8.3} = 109\ \text{µs},$$

$$t_a = \frac{I_{rrm}}{\mathrm{d}I_r/\mathrm{d}t} = \frac{8.3}{1.07 \times 10^5} = 78\ \text{µs} < t_{rr}\quad \text{(constraint satisfied)}.$$

From here `Irrm_ref = 8.3` and `Trr_ref = 2*Qrr_ref/Irrm_ref`. Table 3 gives the same calculation for the floor and for the ceiling.

Using $s$ = 1.2 of the rated point instead of 0.4 lowers $I_{rrm}$ by 20 % for the same charge (5.6 A for the floor) and lengthens $t_{rr}$. It does not change the energy of the commutation loop in a noticeable way, because that energy depends on $I_{rrm}^2$ only through the charge.

**Table 3: recovery parameter sets at the operating point ($a$ = 0.107 A/µs, $s$ = 0.4).**

| Set | Origin | $Q_{rr}$ | $I_{rrm}$ | $t_{rr}$ | $t_a$ |
|---|---|---|---|---|---|
| floor | linear from 0.7 A/µs, 150 °C | 320 µC | 7.0 A | 92 µs | 65 µs |
| **middle (script)** | geometric mean, 100 °C | 450 µC | 8.3 A | 109 µs | 78 µs |
| middle at $T_{vj}$ max | geometric mean, 150 °C | 615 µC | 9.7 A | 127 µs | 91 µs |
| ceiling | straight line of Fig. 4, 150 °C | 1180 µC | 13.4 A | 176 µs | 125 µs |

### 5.4 Q_rr unbalance between the diodes

The diode with the least charge blocks first. It takes the difference $\Delta Q$ on its own capacitor. In the model this is represented with one "weak" diode and five nominal ones.

With a long ramp, (5.2) holds and also $I_{rr} \approx a\tau$. So a diode with charge $(1-u)\,Q_{rr}$ also recovers with a lower current, $\sqrt{1-u}\; I_{rrm}$, and with $t_{rr}$ reduced by the same factor. In the script:

```matlab
Irrm = Irrm_ref*sqrt(1-Max_Qrr_unbalance)
trr  = Trr_ref*sqrt(1-Max_Qrr_unbalance)
Qrr  = Qrr_ref*(1-Max_Qrr_unbalance)       % = 0.5*Irrm*trr (ignored by PLECS)
```

> In other words: $Q_{rr} = a\tau^2$ and $I_{rrm} = a\tau$ both come from the same $\tau$. If the charge is 30 % smaller, $\tau$ is $\sqrt{0.7}$ = 0.84 times smaller, and so are the peak current and the recovery time.

Reducing only $t_{rr}$ while keeping $I_{rrm}$ violates the constraint (5.3): $t_a$ stays at 78 µs while $t_{rr}$ drops to 55 µs for $u$ = 0.5.

With five diodes at the top of the band and one at the bottom, $u$ is the full width of the band:

- ≈ 0.2 for a selected set, ±10 % (banding on $Q_S$, available from Dynex on request [2]);
- ≈ 0.3 for an unselected lot, ±20 %;
- 0.5–0.6 for mixed lots.

---

## 6 Checks on the model

Three quick checks tell whether the parameters were taken in as intended.

1. **Diode waveform at turn-off.** The peak read on the scope must be $I_{rrm}$, and the integral of the reverse current must be $Q_{rr}$ (8.3 A and 0.45 mC for the middle set). If the values come out very different, the $\mathrm{d}i/\mathrm{d}t$ of the circuit does not match `di_dt_ref` (transformer or current changed) and the model is scaling.

2. **Power in $R_{sn}$.** With a matched stack, one must find, per resistor,

   $$P_{R_{sn}} \approx I_{50}^2 R_{sn} + f \left[ \frac{1}{2}\frac{C_{sn}}{n}\frac{V_0^2}{n} + \frac{1}{2}(2L_c)\frac{I_{rrm}^2}{n} \right] = 0.8 + 50\,[0.062 + 0.36] \approx 22\ \text{W}, \tag{6.1}$$

   where $I_{50}$ = 58 mA is the mains-frequency current in $C_{sn}$. The second term is the charging of the stack to $V_0$ at every turn-off (it does not depend on $R_{sn}$). The third term is the energy of the commutation loop at the moment of snap-off, shared between the six resistors. The unbalance adds about $\Delta Q \cdot \hat v$ on the first diode, that is 4–8 W for $u$ = 0.3. The 26 W read in the simulation are consistent.

3. **Power in $R_b$.** $V_{rms}^2/R_b$ with $V_{rms} = 0.634\,\hat V/n$ = 2063 V gives 11.2 W at 380 kΩ. The weak diode keeps an offset $\Delta V \approx (n-1)\Delta Q/(n\,C_{sn})$ of a few hundred volts for the whole blocking period ($R_b C_{sn}$ = 38 ms ≫ 13 ms). It adds $2\langle v\rangle \Delta V / R_b$: with $\Delta V$ = 0.8 kV about 6.5 W, which explains the 18 W read.

---

## 7 Mapping onto the Simscape charge-controlled model (Lauritzen–Ma)

The MATLAB/Simscape twin of the rectifier (model `mv_diode_bridge_design.slx`, folder `matlab_model`) does not use a diode parametrised with $Q_{rr}$, $I_{rrm}$ and $t_{rr}$. It uses the component *RR Diode (Lauritzen–Ma)* of the Secom library, file `diode_rr.ssc` of the package `+diode_rr`: a charge-controlled diode [4].

Its parameters are physical: $I_s$, $N$, $V_t$, $\tau$, $T_M$, $R_s$, $R_r$, $C_{j0}$, $V_{jp}$, $m_g$, $FC$, `dsm`. They must be derived from the same datasheet data of sections 4 and 5. The function `diode_lm_params.m` does this (listing at the end of the section). The mask of the bridge calls it. It receives the structure with the PLECS names (`Vf0`, `rt`, `roff`, `roff_s`, `Cj`, `If0_ref`, `di_dt_ref`, `Qrr_ref`, `Irrm_ref`, plus `Tj` and `N`) and returns the sets $D_n$ for the five nominal diodes and $D_u$ for the unbalanced D11 of each leg. This section derives the formulas that it uses.

### 7.1 The equations of the block

With $v_j$ the junction voltage and $i$ the diode current:

$$v = v_j + R_s\, i, \qquad q_E = \tau I_s \left(e^{v_j/(N V_t)} - 1\right),$$

$$\frac{\mathrm{d}q_M}{\mathrm{d}t} = \frac{q_E - q_M}{T_M} - \frac{q_M}{\tau}, \qquad i = \frac{q_E - q_M}{T_M} + \frac{\mathrm{d}q_j}{\mathrm{d}t} + \frac{v_j}{R_r}. \tag{7.1}$$

Here:

- $q_E$ is the charge that the junction imposes at the edge of the base (exponential law);
- $q_M$ is the charge stored in the base;
- $T_M$ is the transit time with which $q_M$ follows $q_E$;
- $\tau$ is the carrier lifetime;
- $q_j$ is the SPICE depletion charge ($C_{j0}$, $V_{jp}$, $m_g$, limited by $FC$);
- $R_r$ is the parallel leakage resistance, that is the `roff` of PLECS.

In static conduction $q_M = \tau\, i$ and $q_E = (\tau + T_M)\, i$. With the junction reverse biased, $q_E \to 0$ and the current is only what the base gives back: $i = -q_M/T_M$.

### 7.2 From the ramp to the peak and to the tail

With the current forced by the circuit, $i = I_{F0} - a\,t$, the equation of $q_M$ has the solution

$$q_M(t) = \tau\, i(t) + a\tau^2 \left(1 - e^{-t/\tau}\right) \approx \tau\,(i + a\tau) \quad \text{for } t \gg \tau. \tag{7.2}$$

The charge stays behind the current by $a\tau^2$. This is (5.2), used to extrapolate $Q_{rr}$.

The reverse peak happens when the junction empties, $q_E = q_M + T_M\, i = 0$, so

$$I_{rrm} = \frac{a\tau^2}{\tau + T_M} = a\,(\tau - t_{tail}), \qquad t_{tail} = \frac{\tau\, T_M}{\tau + T_M}. \tag{7.3}$$

After the peak, $q_E = 0$, $i = -q_M/T_M$ and $\mathrm{d}q_M/\mathrm{d}t = -q_M\,(1/T_M + 1/\tau)$. The current decays exponentially with time constant $t_{tail}$. The total charge is the triangle of the ramp plus the tail:

$$Q_{rr} = \frac{I_{rrm}^2}{2a} + I_{rrm}\, t_{tail}. \tag{7.4}$$

Figure 3 compares this waveform with the PLECS triangle for the same $Q_{rr}$, $I_{rrm}$ and $a$. The exponential tail, of area $I_{rrm} t_{tail}$, is equivalent to the segment $t_b = 2\,t_{tail}$ of the triangle. So the softness implied by the model is $s = 2\,t_{tail}/t_a$.

The assumption is the long ramp, $(I_{F0} + I_{rrm})/a \gg \tau$. The ratio is $638/93 \approx 6.9$ for the nominal Dynex set and ≈ 4.5 for the worst case. The script warns if it drops below 3.

### 7.3 Inversion: from Q_rr, I_rrm and a to tau and T_M

Equations (7.3) and (7.4) can be inverted in closed form:

$$t_a = \frac{I_{rrm}}{a}, \qquad t_{tail} = \frac{Q_{rr}}{I_{rrm}} - \frac{t_a}{2}, \qquad \tau = t_a + t_{tail}, \qquad T_M = \frac{\tau\, t_{tail}}{t_a}. \tag{7.5}$$

The fit exists only if $t_{tail} > 0$, that is $Q_{rr}/I_{rrm} > I_{rrm}/(2a)$. With $t_{rr} = 2Q_{rr}/I_{rrm}$ this is exactly $I_{rrm} < t_{rr}\, a$, the PLECS constraint (5.3). In the script it is an `assert`. So the two libraries ask the same condition of the datasheet data. The choice $s = 0.4$ of §5.3 makes the PLECS triangle and the Lauritzen–Ma tail carry the same charge.

For the nominal Dynex set ($a = 1.07 \times 10^5$ A/s, $Q_{rr}$ = 450 µC, $I_{rrm}$ = 8.3 A):

$$t_a = \frac{8.3}{1.07 \times 10^5} = 77.6\ \text{µs}, \qquad t_{tail} = \frac{450 \times 10^{-6}}{8.3} - \frac{77.6 \times 10^{-6}}{2} = 15.4\ \text{µs},$$

$$\tau = 77.6 + 15.4 = 93.0\ \text{µs}, \qquad T_M = \frac{93.0 \times 15.4}{77.6} = 18.5\ \text{µs}.$$

**Figure 3 (described).** Diode current at turn-off for the nominal Dynex set ($a$ = 0.107 A/µs, $I_{rrm}$ = 8.3 A). The PLECS triangle and the response of the charge-controlled model with $\tau$ = 93 µs, $T_M$ = 18.5 µs have the same ramp, the same peak and the same charge. The common ramp is $-a\,t$; the PLECS tail is linear with $t_b = 2\,t_{tail}$; the Lauritzen–Ma tail is $e^{-t/t_{tail}}$. Both carry $Q_{rr}$ = 450 µC.

> The same figure, computed from these parameters, is [figure 2 of the physics document](figures/fig2_recovery_waveform.svg).

The unbalance $Q_{rr}(1-u)$, $I_{rrm}\sqrt{1-u}$ of §5.4 scales both $Q_{rr}/I_{rrm}$ and $I_{rrm}/a$ by the same factor $\sqrt{1-u}$. So $t_a$, $t_{tail}$, $\tau$ and $T_M$ of the weak diode are all $\sqrt{1-u}$ times the nominal ones (× 0.837 for $u$ = 0.3).

### 7.4 Conduction: I_s, N and R_s

In static conditions (7.1) gives

$$i = \frac{\tau}{\tau + T_M}\, I_s \left(e^{v_j/(N V_t)} - 1\right), \qquad v = v_j + R_s\, i.$$

The PLECS straight line, $V_{f0} + r_t\, i$, is made to coincide with the model both in value and in slope at $i = I_{F0}$, with $V_t = kT_j/q$ = 32.16 mV at $T_j$ = 100 °C and $N$ = 1:

$$R_s = r_t - \frac{N V_t}{I_{F0}}, \qquad v_j(I_{F0}) = V_{f0} + N V_t, \qquad I_s = \frac{I_{F0}}{e^{v_j/(N V_t)} - 1}\cdot\frac{\tau + T_M}{\tau}. \tag{7.6}$$

The slope of the exponential at $I_{F0}$, $N V_t/I_{F0}$ (0.54 mΩ), takes up more than half of $r_t$. So $R_s$ is small (0.394 mΩ for Dynex, 0.334 mΩ for Infineon), and $N$ cannot exceed $r_t I_{F0}/V_t \approx 1.7$ without making $R_s$ negative.

$I_s$ depends on the recovery set only through $(\tau + T_M)/\tau$, which is the same for $D_n$ and $D_u$: $1.85 \times 10^{-11}$ A for Dynex ($1.88 \times 10^{-11}$ A in the worst case), $1.15 \times 10^{-10}$ to $1.38 \times 10^{-10}$ A for Infineon.

Far from $I_{F0}$ the exponential curve moves away from the straight line. But the losses in the diodes do not enter the sizing of the resistors.

### 7.5 The other parameters

- $R_r$ = `roff` for the unbalanced diode (D11, like `Drr1` in PLECS) and $R_r$ = `roff_s` for the other five: 1.2 and 2.1 MΩ for Dynex (§4.3). For Infineon, with no spread data, `roff_s = roff = 2.9 MΩ`.
- $C_{j0}$ = `Cj` = 0.5 nF with $m_g$ = 0, that is a constant capacitance as in PLECS.
- $V_{jp}$ = 0.7 V, $FC$ = 0.5 and `dsm` = 10 mV are default values that do not affect the results.
- $V_{RRM}$ does not enter the block. The voltage margin must be checked on the waveforms, as in PLECS.

### 7.6 The twelve sets

Table 4 collects the recovery parameters for the two candidate diodes and the three cases, with $u$ = 0.3. In `init_model.m` they are chosen with `diode_type`, `diode_case` and `Max_Qrr_unbalance`. The mask of the bridge calls `diode_lm_params`, and the 36 diodes read `Dn.*` or `Du.*`. The Infineon D711N65T sets ($V_{f0}$ = 0.84 V, $r_t$ = 0.87 mΩ) come from the note `resistor_thermal_note.md`, §7.

**Table 4: Lauritzen–Ma parameters of the twelve sets ($a = 1.07 \times 10^5$ A/s, $I_{F0}$ = 60 A, $u$ = 0.3, $T_j$ = 100 °C, $N$ = 1). $D_n$: nominal diodes; $D_u$: unbalanced D11 ($Q_{rr}$ × 0.7, $I_{rrm}$ × 0.837).**

| Diode | Case | | $Q_{rr}$ (µC) | $I_{rrm}$ (A) | $t_{tail}$ (µs) | $\tau$ (µs) | $T_M$ (µs) | $I_s$ (A) |
|---|---|---|---|---|---|---|---|---|
| Dynex | nominal | $D_n$ | 450 | 8.30 | 15.43 | 93.00 | 18.50 | 1.85 × 10⁻¹¹ |
| | | $D_u$ | 315 | 6.94 | 12.91 | 77.81 | 15.48 | 1.85 × 10⁻¹¹ |
| | worst | $D_n$ | 1200 | 13.40 | 26.94 | 152.17 | 32.73 | 1.88 × 10⁻¹¹ |
| | | $D_u$ | 840 | 11.21 | 22.54 | 127.31 | 27.38 | 1.88 × 10⁻¹¹ |
| | floor | $D_n$ | 320 | 7.00 | 13.00 | 78.42 | 15.59 | 1.85 × 10⁻¹¹ |
| | | $D_u$ | 224 | 5.86 | 10.88 | 65.61 | 13.04 | 1.85 × 10⁻¹¹ |
| Infineon | nominal | $D_n$ | 300 | 6.60 | 14.61 | 76.30 | 18.08 | 1.23 × 10⁻¹⁰ |
| | | $D_u$ | 210 | 5.52 | 12.23 | 63.83 | 15.12 | 1.23 × 10⁻¹⁰ |
| | worst | $D_n$ | 590 | 9.80 | 14.41 | 106.00 | 16.68 | 1.15 × 10⁻¹⁰ |
| | | $D_u$ | 413 | 8.20 | 12.06 | 88.68 | 13.95 | 1.15 × 10⁻¹⁰ |
| | floor | $D_n$ | 190 | 4.80 | 17.15 | 62.01 | 23.71 | 1.38 × 10⁻¹⁰ |
| | | $D_u$ | 133 | 4.02 | 14.35 | 51.88 | 19.84 | 1.38 × 10⁻¹⁰ |

### 7.7 Check

Integrating (7.1) numerically with the current forced (nominal Dynex set), $q_E$ reaches zero at 638.3 µs, with $I_{rrm}$ = 8.300 A and $Q_{rr}$ = 450.0 µC. So (7.5) is exact within the long-ramp assumption. (The script `lm_params_check.py` in the folder repeats the calculation and the integration for all the sets.)

In the Simscape test circuit (driven source with $L$ = 62 mH, rise to 60 A in 1 ms and then $\mathrm{d}i/\mathrm{d}t = -1.07 \times 10^5$ A/s, diode with $R_{sn} + C_{sn}$ in parallel, solver `daessc`, maximum step 0.1 µs), the first negative lobe of the diode current gives the values of Table 5. $I_{rrm}$ is within 2 % (the −1.7 % of the Dynex worst case is the ramp being shorter with respect to $\tau$). $Q_{rr}$ is within 5 % and always in excess, because the lobe also contains the current of $C_j$ and $R_r$.

In the full bridge (Dynex, $u$ = 0.3, grid +10 %, steady state 80–100 ms), the commutation $\mathrm{d}i/\mathrm{d}t$ is $1.14 \times 10^5$ A/s. The diodes recover with $I_{rrm}$ = 8.15 A, $Q_{rr}$ = 458 µC (D12–D16) and 7.48 A, 326 µC (D11). So the losses in the resistors can be compared directly with those of PLECS (§6).

**Table 5: Simscape test circuit at $\mathrm{d}i/\mathrm{d}t = 1.07 \times 10^5$ A/s: measured value / target value of the set.**

| Diode | Case | $D_n$: $I_{rrm}$ (A) | $D_n$: $Q_{rr}$ (µC) | $D_u$ ($u$ = 0.3): $I_{rrm}$ (A) | $D_u$: $Q_{rr}$ (µC) |
|---|---|---|---|---|---|
| Dynex | nominal | 8.29 / 8.30 | 456 / 450 | 6.94 / 6.94 | 323 / 315 |
| | worst | 13.17 / 13.40 | 1174 / 1200 | 11.12 / 11.21 | 837 / 840 |
| | floor | 7.00 / 7.00 | 327 / 320 | 5.86 / 5.86 | 232 / 224 |
| Infineon | nominal | 6.60 / 6.60 | 307 / 300 | 5.52 / 5.52 | 217 / 210 |
| | worst | 9.77 / 9.80 | 594 / 590 | 8.19 / 8.20 | 420 / 413 |
| | floor | 4.80 / 4.80 | 197 / 190 | 4.02 / 4.02 | 140 / 133 |

### 7.8 Listing of `diode_lm_params.m`

```matlab
function [Dn, Du, info] = diode_lm_params(d, u)
% d: struct from init_model.m (PLECS names): Vrrm, roff, roff_s, Cj, Vf0, rt,
%    If0_ref, di_dt_ref, Qrr_ref, Irrm_ref, Tj, N
% u: Max_Qrr_unbalance. Dn, Du: RR Diode (Lauritzen-Ma) parameters
%    for the nominal diodes and for the unbalanced one.
if nargin < 2, u = 0; end
assert(u >= 0 && u < 1, 'Max_Qrr_unbalance must be in [0, 1).');
k_q = 1.380649e-23/1.602176634e-19;
Vt = k_q*(d.Tj + 273.15);
N   = d.N;
a   = d.di_dt_ref;
Dn = one_set(d, d.Qrr_ref,          d.Irrm_ref,          d.roff_s);
Du = one_set(d, d.Qrr_ref*(1 - u), d.Irrm_ref*sqrt(1-u), d.roff);
info.Vt = Vt; info.Trr_n = 2*Dn.Qrr/Dn.Irrm; info.Trr_u = 2*Du.Qrr/Du.Irrm;
    function P = one_set(d, Qrr, Irrm, Rr)
        trr    = 2*Qrr/Irrm;
        assert(Irrm < trr*a, ['Irrm = %.3g A >= trr*di/dt = %.3g A: ' ...
               'no Lauritzen-Ma fit (t_tail <= 0).'], Irrm, trr*a);
        t_tail = Qrr/Irrm - Irrm/(2*a);
        tau    = t_tail + Irrm/a;
        TM     = tau*t_tail*a/Irrm;
        if (d.If0_ref + Irrm)/a < 3*tau
            warning('diode_lm_params:ramp', ['Short ramp: (If0+Irrm)/a = ' ...
                    '%.3g s vs tau = %.3g s; Irrm/Qrr will deviate.'], ...
                    (d.If0_ref + Irrm)/a, tau);
        end
        Rs = d.rt - N*Vt/d.If0_ref;
        assert(Rs > 0, 'rt too small for N = %g: lower N.', N);
        vj = d.Vf0 + N*Vt;
        Is = d.If0_ref/(exp(vj/(N*Vt)) - 1)*(tau + TM)/tau;
        P = struct('Is', Is, 'N', N, 'Vt', Vt, 'tau', tau, 'TM', TM, ...
                   'Rs', Rs, 'Rr', Rr, 'Cj0', d.Cj, 'Vjp', 0.7, 'mg', 0, ...
                   'FC', 0.5, 'dsm', 10e-3, 'Qrr', Qrr, 'Irrm', Irrm, ...
                   'trr', trr, 't_tail', t_tail);
    end
end
```

> The comments inside the listing were translated into English; the code is unchanged.

---

## 8 Data to ask Dynex for

The same three pieces of data close both the PLECS set and, through (7.5) and (7.6), the Simscape set.

- **$Q_S$ and $I_{rr}$ measured at 0.1 A/µs, 60 A, $T_{vj}$ = 100 and 125 °C** (or the ambipolar lifetime of the wafer). They fix `Qrr_ref` and `Irrm_ref` between the floor and the ceiling of Table 3, that is the power of $R_{sn}$ between 12 and 50 W.
- **Reverse current at 3.3 kV for $T_j$ between 50 and 125 °C**, or the banding on leakage. It fixes `roff` and the maximum $T_j$ allowed by $R_b$.
- **Availability and width of the banding on $Q_S$.** It fixes `Max_Qrr_unbalance`.

---

## References

1. Dynex Semiconductor, "DS1112SG rectifier diode," data sheet DS4181-5.0, August 2001.
2. Dynex Semiconductor, "Series and parallel connection of thyristors and diodes," Application Note AN6531.
3. Plexim GmbH, "Diode with Reverse Recovery," PLECS User Manual 5.0, component reference.
4. P. O. Lauritzen and C. L. Ma, "A simple diode model with reverse recovery," IEEE Trans. Power Electron., vol. 6, no. 2, pp. 188–191, 1991.
