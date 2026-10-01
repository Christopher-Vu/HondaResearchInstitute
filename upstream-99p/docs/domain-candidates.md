# Candidate domains

Open decision. The method needs a domain where the space of situations factors into a
grid, so that "gaps" are well defined and can be planted and counted.

## Vehicle

**Perception sensor reliability.** Sensor type (camera, lidar, radar, ultrasonic) x
environmental condition (fog, direct glare, heavy rain, snow, night) x failure mode
(dropout, false positive, range degradation, calibration drift). 4 x 5 x 4 = 80 slots.

The natural gap: sensor and condition pairs that everyone assumes are fine and nobody
has actually measured. Mobility-adjacent and genuinely sparse.

## Fictional domains

Fully invented, so there is no contamination from pretraining and the ground truth
grid is whatever you define.

- **Language documentation.** Take a real language, copy its structure (grammatical
  features and so on), rename it.
- **Building code compliance.** Occupancy type (assembly, residential, industrial, ...)
  x system (egress, fire suppression, ventilation, structural) x requirement category.
  Jurisdictional variation gives you natural contradictions to plant or find.
- **Payments regulation.** A fictional country's payments regime: five license classes
  x six transaction types x obligation categories (capital, reporting, consumer
  disclosure, data residency, settlement timing). Documents are regulatory text,
  supervisory guidance, enforcement actions, industry FAQs.
- **Fraud typology.**
- **Invented materials family.**

## Real narrow domains

Sparse in the wild, so gaps are real rather than engineered.

- Rare languages
- Rare disease
