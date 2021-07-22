This tool allows you to estimate the damage output of Call Of Duty weapons based on your own
ability to recoil control.

### Motivation
Warzone players typically compare the viability of different weapons by comparing
their time-to-kill (TTK).
A weapon's TTK is determined from its damage output
(measured as damage-per-second, or DPS) and the health of a typical enemy player.
Other factors, such as aim-down-sight time and bullet velocity, can be counted
towards TTK to give a more realistic illustration of the weapon's effectiveness in-game.
However, recoil is often treated as an independent weapon characteristic
that is evaluated only qualitatively.
Recoil reduces a player's accuracy when firing automatic weapons at range,
in turn reducing the weapons' damage output.
This reduction scales with the size of the target from the shooter's perspective
(either due to distance or obstruction), as well as the magnitude and shape of the
recoil pattern.
For game balance, developers typically design weapons such that damage and
recoil are roughly correlated.
This way, a higher skill level may be required to
leverage the higher damage potential of certain weapons, while weapons with low damage
output require much less recoil control.

### Recoil
In Warzone, during sustained automatic fire, the magnitude and direction
of the recoil displacement after each round fired is dependent on the 
number of rounds fired so far.
This time-dependence results in a "recoil pattern" that can be learned by players
to improve their accuracy.
Each displacement also has a (typically small) random component added to it in order
to provide some randomness to the recoil pattern.
This "jitter" effectively caps how well a player can use a weapon, since the jitter
displacements are not predictable, but it still rewards quick reactions to correct
for random deviations from the target.

All of these traits make it impractical to quantify the effect of a weapon's recoil
pattern on its accuracy.
One naive approach is to simply measure the horizontal and vertical extent of the
recoil pattern and use these to rank weapons against one another.
This fails to capture the nuances of the time-dependence, as well as
the magnitude of the jitter effects, both of which are arguable equally if not more
important than the maximum displacements.
Even more nuanced metrics for quantifying the recoil pattern morphology may still
fail to capture how well a human player would be able to control the recoil.

### Recoil-adjusted damage simulator

This tool takes an empirical approach to evaluating weapon
recoil: it uses measurements of a human player's accuracy with each weapon to
compute the TTK they would expect to achieve if they were to match that accuracy
when using that weapon in combat.
A player measures their accuracy by firing as accurately as possible at a fixed
target such as a spot on a wall, producing a distribution of bullet impacts on the
wall, and measuring the horizontal and vertical widths of the distribution.
The widths are used to generate a probability distribution of bullet
impacts that can be superimposed on a hypothetical target to compute the expected
damage output rate.
This can be computed for many target sizes to simulate different engagement distances,
yielding an estimate of damage output as a function of target distance.

This assumes that the impact spread approaches some distribution over time.
For simplicity, a two-dimensional normal distribution is assumed.
The validity of this assumption has yet to be tested, but since a player can learn
how to counter-act the time-dependent component of a recoil pattern after some
practice, the impact distribution is likely dominated by the jitter contribution,
at least for more experienced players.
Since the jitter is 
In reality, some weapons can have "kinks" in their recoil patterns that are difficult to
control, even for experts, which can introduce outliers to the bullet spread,
shifting it away from a normal distribution.
The simulated distribution is generated with a standard deviation equal to one-third
of the observed distribution, i.e. it is assumed that the widths measured by the
player cover 99.7% of impacts (this leaves some wiggle room for excluding
extreme outliers about once every few hundred rounds).

### Methodology
The weapon specifications, e.g. damage and fire rate, are extracted from
[TrueGameData](https://truegamedata.com/).
**This means that the results here are
partly limited by how up-to-date and accurate the specs on TrueGameData are!**
To measure a player's effective damage output with a weapon, the player must do the
following:

1. Produce a weapon comparison page on TrueGameData for up to five weapons.
   [Click here](https://www.truegamedata.com/?share=GD6AFu) for an example.
1. Enter a private match, training mode, or a plunder mode with one of their loadouts.
1. Choose a target on a wall on which bullet impacts would be highly visible.
1. Fire a full magazine at the target, controlling recoil to the best of their ability.
1. Measure the horizontal and vertical widths of the impact spread on-screen.
1. Convert the on-screen widths to in-game, angular widths (in degrees).
1. To minimize statistical uncertainty, it is best for the player to do a few trials and
use an average angular width.
1. Repeat the measurement steps for each weapon.

The angular widths are used to produce a probability distribution for each weapon.
These distributions can be visualized using the "Bullet distribution" viewer.
For each weapon, a simulated target map is produced, with values equal to the
damage value of the weapon when hitting each part of the body&mdash;head, chest,
stomach, and extremities.
The target is scaled to simulate engagements over a range of distances (nominally
1-100 meters).
The player can choose where to center the distribution, in order to compare their
recoil-adjusted damage output when aiming at the chest to that at the head,
for instance.

At each distance, the damage per round is computed by multiplying the probability
distribution by the target map and summing the damage contributions.
This is converted to the damage-per-second (DPS), shots-to-kill (STK), and
time-to-kill (TTK) based on target hit points, bullet velocity, and (optionally)
aim-down-sight (ADS) time.
The first round is "free", i.e. it takes on the damage value wherever the distribution
is centered, since recoil does not affect the first round.
If STK exceeds magazine size, the reload time of the weapon (also extracted from
TrueGameData) is added onto the TTK to simulate the time spent to reload in the
middle of an engagement (typically this only occurs for very inaccurate
players or weapons, or when aiming at very distant or small targets).

### Limitations

This method is only a first, admittedly elementary, step towards applying in-game
recoil to damage output. There are a number of shortcomings, some of which
have already been discussed.

Obviously, the damage simulator inputs are dependent on the abilities and device
configurations of the user; reproducibility of results between different users
is not expected, or even likely. One player may find that one weapon yields the
best TTK based on their measurements, but another player who has little experience
controlling the recoil for that same weapon may find that its TTK is far worse when
using this tool. Therefore, results should be treated as personalized predictions
and not used to make broad generalizations about the viability of specific weapons.

The damage simulation assumes that the target is stationary relative to the player.
Against moving targets, a heavier emphasis is placed on low recoil,
among other weapon traits like bullet velocity.
It is also assumed that the target does not shoot back, so accuracy losses caused by
damage flinch or visual distractions are ignored.
Cover is also not taken into consideration, whereas in real game scenarios enemy
targets often hide parts of their body behind cover. That said, the effect of cover
is similar to that of distance: both decrease the target area, punishing high-recoil
weapons more. It can therefore be inferred that the best-performing weapons
as predicted by this tool would also be best against enemies behind cover.

Although measuring recoil through many trials can suppress statistical uncertainty,
systematic uncertainties are inevitable; the variations in recoil patterns
using the same weapon make a perfect measurement of a player's recoil control unfeasible.

Perhaps most importantly, aim assist cannot be accounted for using this method.
However, since aim assist merely alters a controller user's sensitivity near enemies,
the relative ordering of weapon performances measured using this tool is unlikely to
be altered by aim assist, although the raw TTK values would probably be much lower.

Lastly, although the tool covers a wide range of combat distances, the results are best
interpreted for long-range encounters. At close range, so many other factors contribute
to an encounter that recoil is much less of a concern. For this reason, this tool
is recommended only for long-range weapons.

### Example

The following examples are based on measurements and TrueGameData specs taken around July 22,
after the Season 4 Reloaded update (and after the C58 hotfix).

**Below is a video showing an example recoil test from which measurements can be taken.**