This tool allows you to estimate the damage output of Call Of Duty weapons based on your own
ability to recoil control.

### Motivation
Recoil matters!

### Methodology
1. Acquire weapon data from True Game Data
1. Recoil spread for each weapon
1. Sample overlap of recoil spread with enemy hitbox over many distance bins to compute TTK

### Usage
1. Use TGD to design loadouts
1. Measure your recoil spread
1. Interpreting the TTK chart
1. Recoil spread viewer

### Limitations
- Hitbox realism - angles and cover
- Measurement uncertainty - how many trials? 5?
- Shot distribution - uniform vs other
- TGD data

### Future work
This is more or less a reminder for myself about things to implement.
- [ ] Segment plot: horizontal bar showing dominant weapon at each distance bin.
- [ ] Better hitbox geometry, or average over various hitboxes representing different encounter angles.
- [ ] More advanced shot distribution. Tapered uniform distribution? Fit a distribution to actual recoil spreads?
- [x] Add reload time whenever magazine capacity is reached.
- [ ] Add a slider for enemy HP.
- [ ] Add option of including/excluding reload time.
