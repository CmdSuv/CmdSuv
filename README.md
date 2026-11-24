## Hi, I'm Omar Yiğitcan Mengü

I'm an **Anti-Cheat & Kernel-Level Developer** focused on low-level systems programming, operating system internals, and digital forensics. I work close to the metal—analyzing how kernels, binaries, and protocols behave under the hood, building protection and detection mechanisms, and contributing upstream to open-source projects including the **Linux Kernel (`kernel.org`)**, **curl (`curl/curl`)**, **FreeDOS Kernel (`FDOS/kernel`)**, and **Grim Anti-Cheat (`GrimAnticheat/Grim`)**.

---

### Open-Source Contributions

- **Linux Kernel (`kernel.org`)** — Fixed a 64-bit integer overflow (`U64_MAX + 1` → `ZERO_SIZE_PTR` dereference) in `fs/jfs` `dbDiscardAG()` with `dbMount()` validation ([patch](https://lore.kernel.org/r/20261122-jfs-fix-dbdiscardag-overflow-v1-1-c3b3230242dc@gmail.com)) and removed dead code in `staging/most/dim2` ([patch](https://lore.kernel.org/r/20261122-dim2-remove-unused-sysfs-h-v1-1-369ee2d0e438@gmail.com)).
- **curl (`curl/curl`)** — Restricted `--remote-time` (`-R`) timestamp updates in `post_close_output()` to files opened by the transfer, with regression tests ([PR #24133](https://github.com/curl/curl/pull/24133)).
- **FreeDOS Kernel (`FDOS/kernel`)** — Fixed `DosForceDup()` (`INT 21h/AH=46h`) out-of-bounds JFT access and `dup2(h, h)` handle corruption ([PR #279](https://github.com/FDOS/kernel/pull/279)).
- **Grim Anti-Cheat (`GrimAnticheat/Grim`)** — Replaced the legacy 15ms heuristic with deterministic `CLIENT_TICK_END` tick boundaries for queued block places/breaks ([PR #3041](https://github.com/GrimAnticheat/Grim/pull/3041)).

---

### Core Areas

- **Anti-Cheat Development:** Designing runtime integrity checks, packet-level detection logic, memory protection strategies, and analyzing bypass techniques across user-mode and kernel-mode boundaries.
- **Kernel-Level Development:** Working with OS internals, kernel-mode architecture, filesystem & memory management, syscall paths, and low-level system debugging.
- **Low-Level Systems & Forensics:** Memory forensics, binary analysis, execution tracing, artifact investigation, and instruction-level system analysis.

---

### Languages & Technologies

![C](https://img.shields.io/badge/C-A8B9CC?style=flat-square&logo=c&logoColor=black)
![C++](https://img.shields.io/badge/C++-00599C?style=flat-square&logo=cplusplus&logoColor=white)
![x86 / x86-64 Assembly](https://img.shields.io/badge/x86%20%2F%20x86--64%20ASM-6E4C13?style=flat-square&logo=assemblyscript&logoColor=white)
![Java](https://img.shields.io/badge/Java-ED8B00?style=flat-square&logo=openjdk&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)
![Linux Kernel](https://img.shields.io/badge/Linux%20Kernel-FCC624?style=flat-square&logo=linux&logoColor=black)

- **C / C++** — OS kernels, systems programming, kernel/user-mode components, performance-critical development
- **x86 / x86-64 Assembly** — Low-level analysis, 16-bit/64-bit debugging, reverse engineering & internals
- **Java** — Packet-level anti-cheat engines, JVM tooling, and backend systems
- **Python** — Forensics tooling, automation, analysis scripts, and rapid prototyping

---

### What I Focus On

- Analyzing low-level attack surfaces, hooking techniques, and evasion methods
- Building memory inspection, runtime analysis, and forensic utilities
- Writing hardware-aware, performance-critical systems code
- Exploring OS internals and contributing to open-source kernels & anti-cheat engines

---

<div align="center">

<h3>GitHub Stats</h3>

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="./assets/stats-dark.svg" />
    <source media="(prefers-color-scheme: light)" srcset="./assets/stats-light.svg" />
    <img alt="Yigitcan's GitHub Stats" src="./assets/stats-dark.svg" height="175" />
  </picture>
  &nbsp;
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="./assets/langs-dark.svg" />
    <source media="(prefers-color-scheme: light)" srcset="./assets/langs-light.svg" />
    <img alt="Most Used Languages" src="./assets/langs-dark.svg" height="175" />
  </picture>
</p>

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="./assets/streak-dark.svg" />
    <source media="(prefers-color-scheme: light)" srcset="./assets/streak-light.svg" />
    <img alt="Contribution Streak and 30-Day Activity" src="./assets/streak-dark.svg" width="738" />
  </picture>
</p>

</div>
