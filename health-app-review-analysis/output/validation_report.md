# Classifier validation against reference labels

Reference-labelled reviews: **300** (see validation/apply_reference_labels.py for who labelled them and how)

## keyword

- Reviews scored: **300**
- Accuracy (exact label): **51.7%**
- Cohen's kappa: **0.45**
- Complaint vs no-complaint accuracy: **90.7%**

| Label | n (human) | Precision | Recall | F1 |
|---|---|---|---|---|
| billing | 10 | 0.40 | 0.20 | 0.27 |
| paywall | 42 | 0.57 | 0.29 | 0.38 |
| login | 25 | 0.65 | 0.52 | 0.58 |
| crash | 33 | 0.83 | 0.45 | 0.59 |
| performance | 9 | 0.80 | 0.44 | 0.57 |
| food_db | 15 | 0.25 | 0.47 | 0.33 |
| tracking | 5 | 1.00 | 0.40 | 0.57 |
| device_sync | 5 | 0.50 | 0.40 | 0.44 |
| coach_support | 17 | 0.58 | 0.65 | 0.61 |
| spam | 1 | 1.00 | 1.00 | 1.00 |
| ux | 35 | 0.81 | 0.37 | 0.51 |
| content_quality | 14 | 0.00 | 0.00 | 0.00 |
| privacy | 5 | - | 0.00 | - |
| localisation | 1 | 0.00 | 0.00 | 0.00 |
| other_complaint | 13 | 0.13 | 0.69 | 0.21 |
| no_complaint | 70 | 0.74 | 0.91 | 0.82 |

Most common confusions (human -> model):

- paywall -> other_complaint: 11
- crash -> other_complaint: 10
- login -> other_complaint: 8
- paywall -> food_db: 8
- content_quality -> other_complaint: 7
- ux -> other_complaint: 7
- ux -> no_complaint: 7
- food_db -> other_complaint: 5

## llm

- Reviews scored: **300**
- Accuracy (exact label): **93.3%**
- Cohen's kappa: **0.92**
- Complaint vs no-complaint accuracy: **97.7%**

| Label | n (human) | Precision | Recall | F1 |
|---|---|---|---|---|
| billing | 10 | 1.00 | 1.00 | 1.00 |
| paywall | 42 | 1.00 | 0.98 | 0.99 |
| login | 25 | 0.96 | 0.92 | 0.94 |
| crash | 33 | 0.94 | 0.94 | 0.94 |
| performance | 9 | 0.89 | 0.89 | 0.89 |
| food_db | 15 | 0.82 | 0.93 | 0.87 |
| tracking | 5 | 1.00 | 0.80 | 0.89 |
| device_sync | 5 | 1.00 | 1.00 | 1.00 |
| coach_support | 17 | 1.00 | 0.94 | 0.97 |
| spam | 1 | 0.50 | 1.00 | 0.67 |
| ux | 35 | 0.90 | 1.00 | 0.95 |
| content_quality | 14 | 0.88 | 1.00 | 0.93 |
| privacy | 5 | 0.83 | 1.00 | 0.91 |
| localisation | 1 | 0.33 | 1.00 | 0.50 |
| other_complaint | 13 | 0.80 | 0.62 | 0.70 |
| no_complaint | 70 | 0.98 | 0.91 | 0.95 |

Most common confusions (human -> model):

- other_complaint -> content_quality: 2
- no_complaint -> food_db: 2
- other_complaint -> food_db: 1
- paywall -> ux: 1
- no_complaint -> ux: 1
- other_complaint -> privacy: 1
- login -> other_complaint: 1
- login -> ux: 1
