#!/usr/bin/env python3
"""Figures for physics_of_reverse_recovery.md.

Everything is computed from the charge-control (Lauritzen-Ma) diode with
the nominal Dynex DS1112SG60 set of the companion note:

    a    = 1.07e5 A/s   (di/dt forced by the circuit)
    IF0  = 60 A         (forward current before turn-off)
    tau  = 93.0 us      (carrier lifetime)
    TM   = 18.5 us      (transit time)

which gives Irrm = 8.3 A and Qrr = 450 uC, the values written in the
PLECS script.  Run from anywhere:

    python3 make_figures.py

Figures are written as SVG (for the Markdown documents) and PDF (for
the LaTeX documents) next to the script, in ../figures/.
"""

import os

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "figures")
os.makedirs(OUT, exist_ok=True)

# ---------------------------------------------------------------- parameters
A = 1.07e5        # A/s
IF0 = 60.0        # A
TAU = 93.0e-6     # s
TM = 18.5e-6      # s

plt.rcParams.update({
    "font.size": 10,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "figure.dpi": 100,
    "svg.fonttype": "none",
})

PREVIEW = os.environ.get("PREVIEW_DIR")   # optional PNG copies for checking


def save(fig, name):
    """SVG for the Markdown documents, PDF for the LaTeX documents."""
    fig.savefig(os.path.join(OUT, name + ".svg"))
    fig.savefig(os.path.join(OUT, name + ".pdf"))
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        fig.savefig(os.path.join(PREVIEW, name + ".png"), dpi=110)
    plt.close(fig)


C_I = "#1f77b4"      # current
C_Q = "#d62728"      # charge
C_PL = "#2ca02c"     # PLECS triangle
C_GREY = "#7f7f7f"


# ------------------------------------------------------------- the LM diode
def lm_turnoff(a=A, if0=IF0, tau=TAU, tm=TM, dt=0.05e-6, t_end=None):
    """Turn-off of the charge-control diode with the current forced by the
    circuit, i = IF0 - a t, until the junction empties (qE = 0); after that
    the diode blocks and the current is i = -qM / TM.

    Returns time, current, stored charge qM, junction charge qE and the
    index of the peak.  Starts from steady conduction, qM = tau * IF0.
    """
    if t_end is None:
        t_end = (if0 + 2 * a * tau) / a + 8 * tau
    n = int(t_end / dt)
    t = np.arange(n) * dt
    i = np.zeros(n)
    qm = np.zeros(n)
    qe = np.zeros(n)
    qm[0] = tau * if0
    i[0] = if0
    qe[0] = qm[0] + tm * i[0]
    k_peak = None
    for k in range(1, n):
        if k_peak is None:
            # junction still forward biased: circuit sets the current
            i[k] = if0 - a * t[k]
            qm[k] = qm[k - 1] + dt * (i[k - 1] - qm[k - 1] / tau)
            qe[k] = qm[k] + tm * i[k]
            if qe[k] <= 0:
                k_peak = k
                qe[k] = 0.0
                i[k] = -qm[k] / tm
        else:
            # junction empty: the base gives back what it still holds
            qm[k] = qm[k - 1] * np.exp(-dt * (1 / tm + 1 / tau))
            i[k] = -qm[k] / tm
            qe[k] = 0.0
    return t, i, qm, qe, k_peak


t, i, qm, qe, kp = lm_turnoff()
t0 = IF0 / A                       # zero crossing of the current
DEC = 10                           # plot every 10th sample (0.5 µs)
k0 = int(np.argmin(np.abs(t - t0)))
irrm = -i[kp]
ta = t[kp] - t0
t_tail = TAU * TM / (TAU + TM)
qrr = -np.trapezoid(i[k0:], t[k0:])
q_at_t0 = qm[k0]
q_extracted_before_peak = -np.trapezoid(i[k0:kp + 1], t[k0:kp + 1])
q_at_peak = qm[kp]
q_recombined_before_peak = q_at_t0 - q_extracted_before_peak - q_at_peak
q_extracted_tail = -np.trapezoid(i[kp:], t[kp:])
q_recombined_tail = q_at_peak - q_extracted_tail

print(f"t0 = {t0*1e6:.1f} us, Irrm = {irrm:.2f} A, ta = {ta*1e6:.1f} us, "
      f"t_tail = {t_tail*1e6:.1f} us, Qrr = {qrr*1e6:.0f} uC")
print(f"charge at t0: {q_at_t0*1e6:.0f} uC")
print(f"  extracted before the peak : {q_extracted_before_peak*1e6:.0f} uC")
print(f"  recombined before the peak: {q_recombined_before_peak*1e6:.0f} uC")
print(f"  left at the peak          : {q_at_peak*1e6:.0f} uC")
print(f"  extracted in the tail     : {q_extracted_tail*1e6:.0f} uC")
print(f"  recombined in the tail    : {q_recombined_tail*1e6:.0f} uC")

us = 1e6

# ------------------------------------------------- fig 1: charge lags current
fig, ax = plt.subplots(figsize=(7.5, 4.2))
sel = (t <= t0 + 60e-6)
sel[np.arange(len(t)) % DEC != 0] = False
ax.plot(t[sel] * us, i[sel], color=C_I, lw=2, label="diode current  $i(t)$  [A]")
ax.plot(t[sel] * us, qm[sel] / TAU, color=C_Q, lw=2,
        label=r"stored charge  $q(t)/\tau$  [A]")
ax.axhline(0, color="k", lw=0.8)
ax.axvline(t0 * us, color=C_GREY, ls=":", lw=1)
ax.annotate(r"current crosses zero at $t_0$",
            xy=(t0 * us, 0), xytext=(t0 * us - 200, -11),
            arrowprops=dict(arrowstyle="->", color=C_GREY), color=C_GREY)
ax.annotate(r"charge still inside at $t_0$: $a\tau^2$ "
            f"= {q_at_t0*1e6:.0f} µC",
            xy=(t0 * us, q_at_t0 / TAU), xytext=(t0 * us - 460, 14),
            arrowprops=dict(arrowstyle="->", color=C_Q), color=C_Q)
# the horizontal lag of tau
y_mark = 48.0
tx_i = (IF0 - y_mark) / A
tx_q = tx_i + TAU
ax.annotate("", xy=(tx_q * us, y_mark), xytext=(tx_i * us, y_mark),
            arrowprops=dict(arrowstyle="<->", color="k"))
ax.text((tx_i + TAU / 2) * us, y_mark + 2, r"lag = $\tau$", ha="center")
ax.set_xlabel("time  [µs]")
ax.set_ylabel("[A]")
ax.set_xlim(0, (t0 + 60e-6) * us)
ax.set_ylim(-15, 70)
ax.legend(loc="upper right")
ax.set_title("The stored charge follows the current with a delay of one lifetime")
fig.tight_layout()
save(fig, "fig1_charge_lags_current")

# ------------------------------------------- fig 2: the full recovery waveform
fig, ax = plt.subplots(figsize=(7.5, 4.4))
sel = (t >= t0 - 30e-6) & (t <= t0 + 200e-6)
sel[np.arange(len(t)) % DEC != 0] = False
tt = (t[sel] - t0) * us
ax.plot(tt, i[sel], color=C_I, lw=2, label="charge-control diode (Lauritzen–Ma)")
# PLECS triangle with the same Irrm, Qrr and slope: tb = 2 t_tail
tb = 2 * t_tail
tri_t = np.array([0, ta, ta + tb]) * us
tri_i = np.array([0, -irrm, 0])
ax.plot(tri_t, tri_i, color=C_PL, lw=1.5, ls="--",
        label="PLECS triangle, same $I_{rrm}$ and $Q_{rr}$")
ax.fill_between(tt, i[sel], 0, where=(tt >= 0), color=C_I, alpha=0.12)
ax.axhline(0, color="k", lw=0.8)
ax.axvline(ta * us, color=C_GREY, ls=":", lw=1)
ax.annotate("1. ramp forced by the circuit\n    (diode is still a short)",
            xy=(-15, 1.6), xytext=(-25, 4.5), fontsize=9,
            arrowprops=dict(arrowstyle="->", color=C_GREY))
ax.annotate("2. peak: the junction edge\n    runs out of carriers,\n"
            "    the diode starts to block",
            xy=(ta * us, -irrm), xytext=(ta * us + 25, -8.6), fontsize=9,
            arrowprops=dict(arrowstyle="->", color=C_GREY))
ax.annotate("3. tail: the charge left in the\n    middle of the base drains out",
            xy=(ta * us + 35, i[np.argmin(np.abs(t - (t0 + ta + 35e-6)))]),
            xytext=(ta * us + 60, -4.2), fontsize=9,
            arrowprops=dict(arrowstyle="->", color=C_GREY))
ax.text(ta * us / 2, -irrm * 0.45, r"$Q_{rr}$ = " + f"{qrr*1e6:.0f} µC",
        ha="center", color=C_I)
ax.text(ta * us / 2, 0.6, r"$t_a$ = " + f"{ta*us:.0f} µs", ha="center")
ax.text(ta * us + 15, 0.6, r"$t_b$ = " + f"{tb*us:.0f} µs", ha="left",
        color=C_PL)
ax.set_xlabel(r"time after the zero crossing  $t - t_0$  [µs]")
ax.set_ylabel("diode current  [A]")
ax.set_xlim(-30, 200)
ax.set_ylim(-11, 6)
ax.legend(loc="lower left")
ax.set_title("Reverse recovery at the operating point of the note "
             "(0.107 A/µs, nominal Dynex set)")
fig.tight_layout()
save(fig, "fig2_recovery_waveform")

# ------------------------------------------------- fig 3: where the charge goes
fig, ax = plt.subplots(figsize=(7.5, 3.0))
parts = [
    ("extracted before the peak", q_extracted_before_peak, C_I),
    ("extracted in the tail", q_extracted_tail, "#6baed6"),
    ("recombined before the peak", q_recombined_before_peak, C_Q),
    ("recombined in the tail", q_recombined_tail, "#fc9272"),
]
left = 0.0
for name, val, col in parts:
    ax.barh(0, val * 1e6, left=left, color=col, edgecolor="white",
            label=f"{name}: {val*1e6:.0f} µC")
    left += val * 1e6
ax.set_xlim(0, left * 1.02)
ax.set_yticks([])
ax.set_xlabel(r"charge  [µC]   (total inside the base at $t_0$: "
              f"{q_at_t0*1e6:.0f} µC)")
ax.axvline(qrr * 1e6, color="k", ls="--", lw=1)
ax.set_ylim(-0.75, 0.45)
ax.text(qrr * 1e6, -0.58, r"$Q_{rr}$ seen at the terminals = "
        f"{qrr*1e6:.0f} µC", ha="center", va="center")
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.35), ncol=2,
          frameon=False)
ax.set_title("Only about half of the charge inside the diode comes out "
             "as reverse current")
ax.grid(False)
fig.tight_layout()
save(fig, "fig3_charge_budget")

# ------------------------------------- fig 4: the same diode at three slopes
fig, ax = plt.subplots(figsize=(7.5, 4.2))
for a_k, col, lab in [(0.05e6, "#9ecae1", "0.05 A/µs"),
                      (A, C_I, "0.107 A/µs (our circuit)"),
                      (0.3e6, "#08306b", "0.3 A/µs")]:
    tk, ik, qmk, qek, kpk = lm_turnoff(a=a_k)
    t0k = IF0 / a_k
    k0k = int(np.argmin(np.abs(tk - t0k)))
    selk = (tk >= t0k - 20e-6) & (tk <= t0k + 220e-6)
    selk[np.arange(len(tk)) % DEC != 0] = False
    qrrk = -np.trapezoid(ik[k0k:], tk[k0k:])
    ax.plot((tk[selk] - t0k) * us, ik[selk], color=col, lw=2,
            label=f"{lab}:  $I_{{rrm}}$ = {-ik[kpk]:.1f} A, "
                  f"$Q_{{rr}}$ = {qrrk*1e6:.0f} µC")
ax.axhline(0, color="k", lw=0.8)
ax.set_xlabel(r"time after the zero crossing  $t - t_0$  [µs]")
ax.set_ylabel("diode current  [A]")
ax.set_xlim(-20, 220)
ax.legend(loc="upper right")
ax.set_title("Same diode (same τ and $T_M$), three different slopes forced "
             "by the circuit")
fig.tight_layout()
save(fig, "fig4_effect_of_didt")

# ----------------------------------------- fig 5: Qs versus di/dt (log-log)
fig, ax = plt.subplots(figsize=(7.5, 4.4))
a_axis = np.logspace(-1.3, 2, 200)             # A/us
qs_datasheet = 3000 * (a_axis / 3) ** 0.28     # power law through the rated point
a_op = 0.107
floor = 2100 * a_axis / 0.7                    # linear from the last published point
ax.plot(a_axis, qs_datasheet, color=C_I, lw=2,
        label=r"datasheet Fig. 4 (straight line, $Q_S \propto a^{0.28}$)")
ax.plot(a_axis[a_axis < 0.7], floor[a_axis < 0.7], color=C_Q, lw=1.5, ls="--",
        label=r"floor: $Q_S = a\tau^2$ with $\tau$ frozen at 55 µs")
ax.plot(a_axis[a_axis < 0.7], qs_datasheet[a_axis < 0.7], color=C_I, lw=1.5,
        ls=":", label="ceiling: the straight line continued")
ax.plot([3], [3000], "o", color="k", label="rated point: 3 A/µs, 3000 µC")
ax.plot([0.7], [2100], "s", color="k", label="last published point: 0.7 A/µs, 2100 µC")
ax.plot([a_op], [320], "v", color=C_Q)
ax.plot([a_op], [1180], "^", color=C_I)
ax.plot([a_op], [615], "D", color=C_PL, label="geometric mean at 150 °C: 615 µC")
ax.plot([a_op], [450], "*", color="#ff7f0e", ms=11,
        label="value chosen at 100 °C: 450 µC")
ax.axvline(a_op, color=C_GREY, ls=":", lw=1)
ax.text(a_op * 1.08, 130, "our circuit\n0.107 A/µs", fontsize=9, color=C_GREY)
ax.set_xscale("log")
ax.set_yscale("log")
ax.set_xlim(0.05, 100)
ax.set_ylim(100, 10000)
ax.set_xlabel("slope of the current  di/dt  [A/µs]")
ax.set_ylabel(r"recovered charge  $Q_S$  [µC]")
ax.legend(loc="lower right", fontsize=8.5)
ax.set_title("Why $Q_{rr}$ at 0.107 A/µs is an extrapolation, "
             "and the two ways to do it")
fig.tight_layout()
save(fig, "fig5_qs_vs_didt")

# ------------------------------- fig 6: apparent lifetime versus di/dt
fig, ax = plt.subplots(figsize=(7.5, 3.8))
a_axis = np.logspace(-1.3, 2, 200)
tau_app = np.sqrt(3000e-6 * (a_axis / 3) ** 0.28 / (a_axis * 1e6)) * us
ax.plot(a_axis, tau_app, color=C_I, lw=2,
        label=r"apparent lifetime $\sqrt{Q_S/a}$ from the datasheet line")
ax.axhline(55, color=C_Q, ls="--", lw=1.2, label="55 µs: last published point (floor)")
ax.axhline(105, color=C_I, ls=":", lw=1.2, label="105 µs: straight line continued (ceiling)")
ax.axhspan(50, 100, color=C_PL, alpha=0.12,
           label="50–100 µs: plausible true lifetime of a 6 kV wafer")
ax.axvline(a_op, color=C_GREY, ls=":", lw=1)
ax.set_xscale("log")
ax.set_xlim(0.05, 100)
ax.set_ylim(0, 130)
ax.set_xlabel("slope of the current  di/dt  [A/µs]")
ax.set_ylabel("apparent lifetime  [µs]")
ax.legend(loc="upper right", fontsize=8.5)
ax.set_title("The lifetime you back out of the datasheet grows as the ramp "
             "gets slower")
fig.tight_layout()
save(fig, "fig6_apparent_lifetime")

# --------------------------------- fig 7: carrier profiles in the base (sketch)
fig, ax = plt.subplots(figsize=(7.5, 3.8))
x = np.linspace(0, 1, 400)
shapes = [
    ("conduction (before the ramp)", 1.0 - 0.15 * np.cos(np.pi * x) ** 2, "#08306b"),
    (r"at $t_0$ (zero current)", 0.55 - 0.08 * np.cos(np.pi * x) ** 2, C_I),
    ("at the peak (edges empty)", 0.30 * np.sin(np.pi * x) ** 1.6, C_Q),
    ("in the tail", 0.10 * np.sin(np.pi * x) ** 1.6, "#fc9272"),
]
for lab, y, col in shapes:
    ax.plot(x, y, color=col, lw=2, label=lab)
ax.axvspan(-0.08, 0, color="#cccccc")
ax.axvspan(1, 1.08, color="#cccccc")
ax.text(-0.04, 0.5, "p+", ha="center", va="center", fontsize=11)
ax.text(1.04, 0.5, "n+", ha="center", va="center", fontsize=11)
ax.text(0.5, 1.0, "n− base (the thick, lightly doped layer that holds the voltage)",
        ha="center", fontsize=9, color=C_GREY)
ax.set_xlim(-0.08, 1.08)
ax.set_ylim(0, 1.45)
ax.set_xticks([])
ax.set_yticks([])
ax.set_xlabel("position across the base")
ax.set_ylabel("density of the stored carriers (plasma)")
ax.legend(loc="upper center", fontsize=8.5, ncol=2)
ax.set_title("Sketch: the plasma in the base empties during turn-off "
             "(illustrative shapes)")
ax.grid(False)
fig.tight_layout()
save(fig, "fig7_plasma_profiles_sketch")

# ---------------------------------- fig 8: nominal versus weak diode (u = 0.3)
u = 0.3
f = np.sqrt(1 - u)
tn, i_n, _, _, kpn = lm_turnoff()
tw, i_w, _, _, kpw = lm_turnoff(tau=TAU * f, tm=TM * f)
fig, ax = plt.subplots(figsize=(7.5, 4.2))
seln = (tn >= t0 - 20e-6) & (tn <= t0 + 200e-6)
seln[np.arange(len(tn)) % DEC != 0] = False
selw = (tw >= t0 - 20e-6) & (tw <= t0 + 200e-6)
selw[np.arange(len(tw)) % DEC != 0] = False
ax.plot((tn[seln] - t0) * us, i_n[seln], color=C_I, lw=2,
        label=f"nominal diode: $Q_{{rr}}$ = 450 µC, $I_{{rrm}}$ = {-i_n[kpn]:.1f} A")
ax.plot((tw[selw] - t0) * us, i_w[selw], color=C_Q, lw=2,
        label=f"weak diode ($u$ = 0.3): $Q_{{rr}}$ = 315 µC, "
              f"$I_{{rrm}}$ = {-i_w[kpw]:.1f} A")
ax.fill_between((tn[seln] - t0) * us, i_n[seln],
                np.interp(tn[seln], tw, i_w), where=((tn[seln] - t0) >= 0),
                color=C_PL, alpha=0.25,
                label=r"$\Delta Q$ = 135 µC: goes into the snubber capacitor "
                      "of the weak diode")
ax.axhline(0, color="k", lw=0.8)
ax.set_xlabel(r"time after the zero crossing  $t - t_0$  [µs]")
ax.set_ylabel("diode current  [A]")
ax.set_xlim(-20, 200)
ax.legend(loc="upper right", fontsize=9)
ax.set_title("In a series stack the diode with less charge blocks first")
fig.tight_layout()
save(fig, "fig8_unbalance")

print("figures written to", os.path.abspath(OUT))
