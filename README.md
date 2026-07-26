# BankSight

BankSight is a customer segmentation and personalization platform for retail banking.

It helps banks understand customer behaviour by analysing transaction data and  grouping customers into different segments and recommending suitable banking products. Instead of manually exploring the data the  users can simply ask questions through the chat interface.

## Overview

Banks have large amounts of customer data, but finding useful insights from it can take time.

BankSight makes this easier. It reads the customer data and  performs the required analysis and returns the results in a simple and understandable way. Depending on the question, it can segment customers, explain why a customer belongs to a segment or to recommend products or to analyse trends and evaluate the segmentation model.

## Running Locally

Clone the repository.

```bash
git clone <repository-url>
cd BankSight
```

Install the required packages.

```bash
pip install -r requirements.txt
```

Run the application.

```bash
streamlit run agent/app.py
```

The dataset is already included in the repository so no additional setup is required.

## Project Structure

```text
BankSight
│
├── agent/
│   ├── app.py
│   ├── pipeline.py
│   ├── segmentation.py
│   ├── recommendations.py
│   ├── explainability.py
│   ├── personas.py
│   ├── intent_parser.py
│   └── trends.py
│
├── data/
├── requirements.txt
└── README.md
```

## Architecture

Every question follows the same flow.

```text
User Query
      │
      ▼
Intent Parser
      │
      ▼
Tool Selection
      │
 ┌────┼───────────────┐
 │    │               │
EDA  Segmentation  Explainability
 │
Recommendations
 │
Trend Analysis
 │
Model Evaluation
 │
      ▼
Response
```

Only the tools needed for that question are used. If more information is required, the application asks the user before continuing.

### Fallback Mechanism

BankSight uses an LLM to generate responses.

If the LLM is unavailable, the application switches to a rule-based system. This keeps the main features working, including segmentation, recommendations and explainability.

## Dataset

This project uses the **Bank Customer Segmentation** dataset by Shivam Bansal.

The dataset contains more than one million banking transactions. After preprocessing, it contains around **882,600 unique customers**.

The repository already includes the dataset used for this project.

## Data Cleaning

The data is cleaned before any analysis is performed.

The preprocessing pipeline:

- Fixed around **57,339** invalid date of birth values (`01/01/1800`)
- Standardized gender labels
- Cleaned location names
- Removed invalid records
- Clipped negative balances and transaction amounts
- Created customer-level features from transaction history

## Segmentation Strategy

Customers are grouped into three segments.

- Priority
- Regular
- Dormant

The segmentation is based on simple business rules.

A customer becomes **Priority** only if they have both a high account balance and a high transaction volume. This helps separate active high-value customers from customers who only maintain a high balance.

Since the rules are transparent, every customer can also be explained easily.

## Example Queries

- Segment customers into priority, regular and dormant customers.
- Why is customer `C1010011` a priority customer?
- Recommend products for dormant customers.
- Which regular customers could become priority customers?
- Which customers are at risk of becoming dormant?
- Show customer distribution by location.
- What is the average transaction amount for priority customers?
- Evaluate the segmentation model.
- Generate customer personas.

## Key Design Decisions

### Transaction Frequency

At first, transaction frequency was planned as one of the segmentation features.

After analysing the data, we found that transaction counts were almost the same for most customers. This happened because the dataset covers only a short period of time.

Instead, we used **Total Transaction Volume** since it gives a better picture of customer engagement.

### Priority Customers

Priority customers must satisfy both the balance threshold and the transaction volume threshold.

Using both conditions helps identify customers who are valuable and actively using the bank instead of customers who only have a high balance.

### Dormant Customers

The last segment is called **Dormant**.

After analysing customer recency, we found very little difference between the three segments.

| Segment | Average Recency (Days) |
|---------|-----------------------:|
| Priority | 54.3 |
| Regular | 55.3 |
| Dormant | 56.6 |

Because of this, the Dormant segment should not be treated as inactive customers.

Instead, it represents customers with low balances and low transaction volume.

## Limitations

- The dataset covers only a short period so recency is not a reliable feature.
- Transaction frequency showed very little variation and could not be used for segmentation.
- The current segmentation is rule-based so  it is easy to understand but may miss more complex customer behaviour.
- Product recommendations are based on business rules.
- If the LLM is unavailable, the application switches to the built-in rule-based response system.

## Future Work

- Add ML-based segmentation.
- Improve product recommendations.
- Add SHAP explainability.
- Support real-time transaction data.
- Deploy the application to the cloud.