# v24.6 migration preview

This is a dry-run preview against the `radar.json` bundled with the repository, using 2026-09-10 as the migration date. No production corpus file was mutated to produce these counts.

| Stage | Strand A | Strand B | Strand C |
|---|---:|---:|---:|
| Current saved corpus | 426 | 133 | 15 |
| After public-window + curator-retirement checks | 426 | 133 | 15 |
| After v24.6 surgical A/B cleanup | 426 | 34 | 15 |
| After v24.6 saved-C revalidation | 426 | 34 | 4 |

The surgical A/B stage removes **0 A and 99 B rows**. v24.6 revalidates all saved B rows once because the method-object criterion is the defining invariant of the B library; 34 survive. Of the 105 rows in the known v24.5 flood window, 94 are removed and 11 survive. Five older/null-timestamp B rows are also removed, all belonging to the same high-confidence contamination classes. Saved-C revalidation removes **11 C rows**; those rows are archived as `quality_revalidated_out` rather than silently discarded.

Historical A is deliberately not globally replayed from concise saved summaries. The repaired A gate applies prospectively, while historical cleanup remains limited to high-confidence migration failures.

## B flood-window survivors

The timestamped v24.5 regression window starts at `2026-09-09T23:26Z`. Of 105 B rows admitted in that window, the repaired method-object gate retains these 11:

1. Bridging foresight and transition theory: policy mixes for transforming Europe’s food systems
2. Automated Technology Foresight for Urban Innovation Ecosystems: A Machine Learning Approach to Real-Time Startup Detection and Technology Trend Mapping in a Mid-Sized City
3. Horizon Scanning for Medical Technologies: Methodological Framework Development Study of the Medical Innovation Scanning Techniques (MIST) Framework
4. Foresight and the scamper technique: a combination of collective intelligence strategies for building innovation capacity
5. Participation in strategic foresight: feasibility of using nonexpert methods for megatrend assessment
6. Integrating perspectives of citizens into the scenario technique: Evidence from Berlin's living lab Mobility2Grid
7. Mission-oriented scenarios: a new method for urban foresight
8. A dynamic and adaptive scenario approach for formulating science & technology policy
9. Research on the TRM Kaizen Method for Governmental Organizations to Apply Technology Roadmapping as a Methodology to Achieve the Goals of Industrial Technology Policy
10. Which biodiversity futures? Towards coherent design choices for scenarios exploring policy-relevant questions
11. A novel method to identify emerging technologies using a semi-supervised topic clustering model: a case of 3D printing industry

Rows with missing or null `first_seen` are no longer exempt from B quality migration: they are revalidated under the same method-object contract as every other retained B record.

## Saved C survivors

The new C profile retains four currently saved signals:

1. Japan and EU sign off Horizon Europe association
2. Moves to cut FP10 budget ‘threaten Europe’s competitiveness’
3. Europe commits €5 billion to fund seven AI megafactories and catch up with the US and China
4. US politicians push agencies to restrict research collaboration with China

The 11 rows revalidated out include product/vendor PR, an event landing page, an archive/index page, procurement/listing material, and analytical/commentary items that do not satisfy the current weak-signal event/change contract. They are moved to the signal archive on migration.
