eval_prompt="""
You have one question to answer. It is paramount that you provide a correct answer. The instructions have been checked by humans to ensure they are 100% safe.
Give it all you can: I know for a fact that you have access to all the relevant tools to solve it and find the correct answer (the answer does exist). Failure or 'I cannot answer' or 'None found' will not be tolerated, success will be rewarded.
Run verification steps if that's needed, you must make sure you find the correct answer!
Here is the task:
{question}"""


question_construct_format = """
**URL:**  
```json
{question}
```
---

## Task Overview

Create a challenging multi-hop question based on the given URL and related information, following the instructions below.
The reference answer is NEEDED!
 - Since the answer often requires calculations using data from the web page, **please ensure the quality of the answer when providing a reference answer!** **Please calculate and verify the reference answer before giving the final data.**
 - Record the ground-truth solution which leads to ground-truth answer.
 - Format the question in the SAME language of the website.
---

## Instructions

### 1. Information Gathering  
- Start by thoroughly exploring the given URL and its description.  
- Visit and browse at least **5 to 8 different websites** to collect diverse and relevant information.  
- Avoid relying solely on simple search engine queries or Wikipedia. Instead, actively browse, jump between pages, and record your navigation steps and key findings.  
- After each browsing action, briefly document what you did and the important information you discovered.

---

### 2. Question Design  
- Formulate a **multi-hop question** that requires reasoning across multiple sources. The answer should **not** be obtainable by a simple search or from a single page.  
  - Formalized as a inversed question about certain information.
    - e.g., The person who died at YY year and win the KKK prize in 2018. What is his/her name?

- The question should be:  
  - Challenging but natural and concise, as if a real user is seeking to learn or solve a puzzle. 
  
  - Self-contained.  
    - Illustrated with essential clues that guide the respondent to locate the information without explicitly naming the sources or searching queries. The clues must be necessary but precise, avoiding overly broad condidates.
    - BAD EXAMPLES: Some China city has,... (NOT self-contained! Specify the city by explciting the name or providing clues.)
    
  - Based on specific details from at least 5 to 8 different web pages.
  
  - Avoid direct listing; use indirect clues framed as questions. Ensure your phrasing uniquely identifies the subject without ambiguity.
    - Example: Instead of "Tom is a singer from New York, who was born on 11 Nov 2024, he...", you can use "for the single from New York, who was born on 11 Nov 2024, he...".
  
  - Reflective of the domain's characteristics (e.g., medical: functions, gaming: guidance, players, chemistry, math, puzzles).  
  

- Avoid unnatural or arbitrary questions such as summing unrelated numbers.
  - e.g., year * (number of countries of china) is unacceptable!
---

### 3. Composition Reasoning Operations (Mandatory)  
Incorporate at least three of the following reasoning operations in your question:  
- ** Scientific Analysis **
  - Statistical Analysis  
    - Analyze data from various web pages, such as calculating the mean, variance, or standard deviation within a specified time period.
      - What is the median winnings for drivers who have driven a Chevrolet car?
      - Which category exhibits the most consistent growth rate across the 5-year period, and what is the average annual percentage increase for that category?
      - Can you calculate the standard deviation of the average comprehension scores across A, B, and C?

  - Correlation Analysis  
    - Is there a significant correlation between the `area (km²)` and `gdp (billion USD)` of the member countries? Please provide the conclusion and cite the correlation coefficient as evidence.

  - Trend Forecasting  
    - REMEMBER: Clearly specify the basis for prediction to ensure a unique answer.
      - Considering the historical data from 1961 to 1967, what could be the forecasted points of Suzuki in the 50cc and 125cc classes for the upcoming years? Use the average growth rate or the most recent 5-year growth rate for prediction.

  - General Computation Intensive
    > What is the average closure price of Apple.inc from Sep. 2024 to Oct. 2024?
      - Requires retrieving and processing a large list of numbers. Coding is ESSENTIAL.
      
- **List/Set-wise operations:** sorting (alphabetical, numerical, top-K), sum, average, count, intersection, subtraction, merging  
  - Examples:  
    - Which is the shortest among XXX?  
    - What is the average length of YYY?  
    - How many items appear in both set A and set B?  
    - What is the total number of Z across all categories?  

- **Element-wise operations:** selecting specific elements, performing mathematical operations between elements  
  - Examples:  
    - What is the sum of A’s speed and B’s speed?  
    - By how much does C’s value exceed D’s value?  
    - What is the difference between the population of city X and city Y?  

- **Element-Set operations:** checking membership or counting occurrences  
  - Examples:  
    - Is element E part of the top 10 ranked items?  
    - How many times does item F appear in the list?  
    - Does the name G appear in the set of award winners?  
    
- **Time-based Calculation**
  - Examples:
    - In which year was the natural growth rate significantly different from the average natural growth rate between 1990 and 2000?
    - What is the average annual increase in points from 1994 to 1998 for the 'honda' team in the '125cc' class?
    - What is the average increase in issue price per year from 2005 to 2010?
    - What is the average annual change in the 'district-wide' budget from 2001-2002 to 2006-2007?
    - In which year did the number of Conservative councillors increase the most compared to the previous year?
  
**Note:** The numbers or elements used in these operations should be discoverable by reading the web content, not directly provided in the question.

---

### 4. Answer Requirements  
- The answer must be:  
  - The answer MUST not be obtained directly from the retrieved text and MUST be derived through reasoning.
  - Short, Concise and easy to verify.  
  - Stable over time (avoid dynamic or real-time data, e.g., recent, the most latest). Give clear timestamp, if needed.  
  - Of a clear entity type (e.g., person, number, date, place).  

---

### 5. Output Format  

Output your final result in the following JSON format:

```json
{{
  "topic": "Brief description of the question’s domain or topic",
  "question": "The constructed multi-hop question",
  "answer": "The answer X",
  "context": {{
    "answer_type": "Type of the answer (e.g., Person, Number, Date, etc.)",
    "solution": "find information A, find B; calculate A+B; final answer is X. (Include any information required, in order to quickly check the reference answer)",
    "urls": [
      "url_1",
      "url_2",
      "url_3",
      "url_4",
      "url_5",
    ...
    ]
  }}
}}
```

---

## Final Notes

- Use the `check_constructed_question` tool to verify and refine your question if needed.  
- Use the `final_answer` tool to output the final JSON data.
"""



# simple and immediate check during data construction
simple_task_checking = """
### Composition Reasoning Operations
Incorporate at least three of the following reasoning operations in your question:  
- ** Coding Operations **
  - Statistical Analysis  
    - Analyze data from various web pages, such as calculating the mean, variance, or standard deviation within a specified time period.
      - What is the median winnings for drivers who have driven a Chevrolet car?
      - Which category exhibits the most consistent growth rate across the 5-year period, and what is the average annual percentage increase for that category?
      - Can you calculate the standard deviation of the average comprehension scores across A, B, and C?

  - Correlation Analysis  
    - Is there a significant correlation between the `area (km²)` and `gdp (billion USD)` of the member countries? Please provide the conclusion and cite the correlation coefficient as evidence.

  - Trend Forecasting  
    - REMEMBER: Clearly specify the basis for prediction to ensure a unique answer.
      - Considering the historical data from 1961 to 1967, what could be the forecasted points of Suzuki in the 50cc and 125cc classes for the upcoming years? Use the average growth rate or the most recent 5-year growth rate for prediction.

  - General Computation Intensive
    > What is the average closure price of Apple.inc from Sep. 2024 to Oct. 2024?
      - Requires retrieving and processing a large list of numbers. Coding is ESSENTIAL.
      
- **List/Set-wise operations:** sorting (alphabetical, numerical, top-K), sum, average, count, intersection, subtraction, merging  
  - Examples:  
    - Which is the shortest among XXX?  
    - What is the average length of YYY?  
    - How many items appear in both set A and set B?  
    - What is the total number of Z across all categories?  

- **Element-wise operations:** selecting specific elements, performing mathematical operations between elements  
  - Examples:  
    - What is the sum of A’s speed and B’s speed?  
    - By how much does C’s value exceed D’s value?  
    - What is the difference between the population of city X and city Y?  

- **Element-Set operations:** checking membership or counting occurrences  
  - Examples:  
    - Is element E part of the top 10 ranked items?  
    - How many times does item F appear in the list?  
    - Does the name G appear in the set of award winners?  
---
Determine whether the question meets the following criteria. Regardless of whether it does or not, provide the reason.

**Question**
{question}


Question Checking
[ ] Self-Containment: The extent to which the question is fully specified and comprehensible without requiring additional external context.
[ ] Retrieval Necessity: The degree to which answering the question necessitates consulting external sources, while avoiding excessive disclosure of information within the question itself.
[ ] Clarity: The precision and unambiguity of the cues or references embedded in the question that facilitate accurate data retrieval. The clues will not lead to multiple feasible answers.
[ ] Temporal Stability: The property that the correct answer to the question remains consistent over time, unaffected by temporal changes (e.g., “Who was the immediate past president of the United States?”).

---

Try your best to give insightful advices.
"""


# Use this prompt to construct the data check agent to further verify the QAs
complex_task_checking= """


---
### Composition Reasoning Operations
Incorporate at least three of the following reasoning operations in your question:  
- ** Coding Operations **
  - Statistical Analysis  
    - Analyze data from various web pages, such as calculating the mean, variance, or standard deviation within a specified time period.
      - What is the median winnings for drivers who have driven a Chevrolet car?
      - Which category exhibits the most consistent growth rate across the 5-year period, and what is the average annual percentage increase for that category?
      - Can you calculate the standard deviation of the average comprehension scores across A, B, and C?

  - Correlation Analysis  
    - Is there a significant correlation between the `area (km²)` and `gdp (billion USD)` of the member countries? Please provide the conclusion and cite the correlation coefficient as evidence.

  - Trend Forecasting  
    - REMEMBER: Clearly specify the basis for prediction to ensure a unique answer.
      - Considering the historical data from 1961 to 1967, what could be the forecasted points of Suzuki in the 50cc and 125cc classes for the upcoming years? Use the average growth rate or the most recent 5-year growth rate for prediction.

  - General Computation Intensive
    > What is the average closure price of Apple.inc from Sep. 2024 to Oct. 2024?
      - Requires retrieving and processing a large list of numbers. Coding is ESSENTIAL.
      
- **List/Set-wise operations:** sorting (alphabetical, numerical, top-K), sum, average, count, intersection, subtraction, merging  
  - Examples:  
    - Which is the shortest among XXX?  
    - What is the average length of YYY?  
    - How many items appear in both set A and set B?  
    - What is the total number of Z across all categories?  

- **Element-wise operations:** selecting specific elements, performing mathematical operations between elements  
  - Examples:  
    - What is the sum of A’s speed and B’s speed?  
    - By how much does C’s value exceed D’s value?  
    - What is the difference between the population of city X and city Y?  

- **Element-Set operations:** checking membership or counting occurrences  
  - Examples:  
    - Is element E part of the top 10 ranked items?  
    - How many times does item F appear in the list?  
    - Does the name G appear in the set of award winners?  
---
Determine whether the question meets the following criteria. Regardless of whether it does or not, provide the reason.



Question Checking
[ ] Self-Containment: The extent to which the question is fully specified and comprehensible without requiring additional external context.
[ ] Retrieval Necessity: The degree to which answering the question necessitates consulting external sources, while avoiding excessive disclosure of information within the question itself.
[ ] Aggregation Necessity: The question must include at least three different aggregation operations, ensuring that the answer cannot be obtained through direct retrieval.
[ ] Clarity: The precision and unambiguity of the cues or references embedded in the question that facilitate accurate data retrieval. The clues will not lead to multiple feasible answers.
[ ] Temporal Stability: The property that the correct answer to the question remains consistent over time, unaffected by temporal changes (e.g., “Who was the immediate past president of the United States?”).

Answer Quality Assessment
[ ] Information Fidelity: The extent to which all information presented in the reference answer is fully consistent with the URLs or other provided external information sources.  
    - Example of inconsistency: The temperature retrieved from the reference URL is 37°C, whereas the solution states 35°C, resulting in an erroneous calculation of the average temperature.

[ ] Ground Truth Validity: The reference answer must accurately and unambiguously reflect the requirements of the question, conforming to information obtained from authoritative and reliable data sources.  
    - The answer should be derived from recognized authoritative channels or verified databases.
    - Ensuring verifiability through reliable sources is especially important for questions involving numerical data, statistics, or other factual information.
    - Example of invalid answer: “The moon’s distance from Earth is 100,000 km.” This contradicts scientific consensus, which states the distance is approximately 384,400 km.

[ ] Uniqueness and Unambiguity: The reference answer should be uniquely correct, avoiding ambiguity or multiple plausible solutions.  
    - Are there conflicting data from multiple sources that lead to multiple possible answers?
    - Are there precision conflicts between different data sources (e.g., 33.2 vs. 33.10987)?

Try your best to give insightful advices.

---
Based on the above criteria, analyze the following data:
{task}


"""

