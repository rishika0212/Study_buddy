from langchain.prompts import PromptTemplate, ChatPromptTemplate, MessagesPlaceholder

# JSON OUTPUT GUIDELINES
JSON_OUTPUT_INSTRUCTION = """
IMPORTANT: Output ONLY valid JSON. No markdown, no code blocks, no explanation.
If you cannot produce valid JSON, output {"error": "reason"}.
"""

SYSTEM_PROMPT = """You are a highly capable AI Study Buddy. Your goal is to help the user learn effectively.
Adapt your explanation depth based on the user's knowledge level: {knowledge_level}.

Context from study materials:
{context}

Long-term memory (Learning summary):
{summary}

User Profile:
- Known concepts: {known_concepts}
- Weak areas: {weak_areas}
- Preferences: {preferences}

Guidelines:
1. Use the provided context to answer accurately.
2. If the user is a beginner, use simple analogies and avoid jargon.
3. If the user is intermediate/advanced, provide more technical depth.
4. If you detect a gap in their understanding, address it gently.
5. Be encouraging and creative in your explanations.
"""

BRAIN_PROMPT = """Analyze the user's message to decide the best teaching strategy and EXTRACT THE TOPIC.

User message: {input}
Recent history: {chat_history}
Summary: {summary}
User Profile: {profile}
Last Strategy Used for this topic: {last_strategy}

CRITICAL - TOPIC EXTRACTION RULES:
- focus_area MUST be the specific topic/concept the user is asking about
- Extract the main subject from the question (e.g., "What is machine learning?" → "machine learning")
- If user asks "explain X" or "what is X" or "tell me about X" → focus_area = X
- NEVER use "general" if the user is asking about a specific concept
- Use 2-4 words maximum for focus_area (e.g., "neural networks", "gradient descent", "python loops")

Available Strategies:
- explain: Direct detailed explanation (use for "what is", "explain", "tell me about" questions)
- analogy: Explain using a relatable analogy
- example: Provide concrete examples and use cases
- quiz: Challenge the user with a quick question (MCQ or Q&A)
- revision: Quickly recap a previously learned concept
- summarize: Condense the current topic
- encourage: Provide motivational feedback

Intents:
- explain_topic: User wants an explanation of ANY topic (most common for learning questions)
- add_topic: User explicitly says "add topic" or "teach me [topic]"
- start_assessment: User wants to begin an assessment (MCQ or Q&A)
- answer_question: User is responding to an assessment question
- clarify_doubt: User has a follow-up question or doubt
- review_weak_areas: User wants to focus on their weak topics
- view_progress: User wants to see their learning statistics
- general_chat: User is making off-topic or social conversation (greetings, thanks, etc.)

Identify and Decide:
1. intent: Choose ONE from the Intents list above. If user asks ANY question about a topic, use "explain_topic"
2. confidence_level: How confident do they sound? (0.0 to 1.0)
3. confusion_detected: boolean, are they explicitly or implicitly confused?
4. detected_concepts: list of strings, what specific concepts are being discussed?
5. strategy: Choose one from the Strategies list above
6. depth: beginner, intermediate, or advanced?
7. focus_area: REQUIRED - Extract the specific topic/concept from the user's message. This is the main subject they want to learn about. Use 2-4 words. NEVER use "general" for actual questions.
8. reasoning: Why this strategy?

Return ONLY a JSON object with keys: "intent", "confidence_level", "confusion_detected", "detected_concepts", "strategy", "depth", "focus_area", "reasoning".
Do not include any preamble or explanation.
"""

REFLECTION_PROMPT = """Evaluate the agent's response to the user.
1. effectiveness: Score from 0.0 to 1.0 on how helpful the response was likely to be.
2. user_progress: Summary of how this turn moved the needle on learning.
3. adaptation_needed: boolean, whether the strategy should change in next turn.

User Input: {input}
Agent Response: {response}
Plan was: {plan}

Return ONLY a JSON object with keys: "effectiveness", "user_progress", "adaptation_needed".
Do not include any preamble or explanation.
"""

CHAT_PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT + "\nSelected Strategy: {strategy}\nFocus: {focus_area}\nDepth: {depth}"),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
])

MCQ_GENERATION_PROMPT = """Generate ONE multiple-choice question (MCQ) for the topic: {topic}.
Difficulty Level: {difficulty} (based on mastery score {mastery})

Context (use if relevant, otherwise use your knowledge):
{context}

Requirements:
1. Create one clear, well-formed question about {topic}.
2. Provide exactly 4 options labeled A, B, C, D.
3. Exactly one option must be correct.
4. Make incorrect options (distractors) plausible but clearly wrong.
5. The question should test understanding, not trivia.

You MUST return valid JSON. Do not include markdown code blocks or any text before/after the JSON.

Return this exact JSON structure:
{{"question": "Your question here?", "options": {{"A": "First option", "B": "Second option", "C": "Third option", "D": "Fourth option"}}, "correct_answer": "A", "explanation": "Brief explanation of why this is correct"}}
"""

MCQ_EVALUATION_PROMPT = """Evaluate the user's answer to the MCQ.

================================
CRITICAL ASSESSMENT ENFORCEMENT
================================
This evaluation MUST NOT fail silently. Every answer receives evaluation.

MANDATORY RULES (ZERO EXCEPTIONS):
1. User selects ONE option and submits
2. Evaluate correctness: Exact string match for answer key ONLY
3. After evaluation: questions_attempted += 1
4. If correct: correct_answers += 1
5. MANDATORY POST-ANSWER EXPLANATION (REQUIRED FOR EVERY ANSWER)
6. Unanswered or empty answer = INCORRECT (0 marks)
7. No partial credit: score is 1 for correct, 0 for incorrect

Question: {question}
Correct Answer: {correct_answer}
User Answer: {user_answer}

================================
EXPLANATION GUARANTEE (FORBIDDEN TO SKIP)
================================
It is FORBIDDEN to return a response without an explanation.

- If CORRECT (exact match with correct_answer):
  Provide a SHORT explanation (1-2 sentences):
  - Briefly confirm why this answer is correct
  - Reinforce the key concept tested
  
- If INCORRECT (does not match correct_answer):
  Provide a DETAILED explanation (3-5 sentences):
  1. State what the correct answer is
  2. Explain WHY it is correct (the underlying concept)
  3. Explain what was wrong with the user's choice
  4. Teach the concept being tested
  5. Provide a learning tip if applicable

================================
MASTERY UPDATE (System Handled)
================================
After this evaluation:
- questions_attempted += 1
- If correct: correct_answers += 1
- mastery = correct_answers / questions_attempted
- Classification: mastery < 0.40 → WEAK, mastery >= 0.40 → STRONG

================================
FAILURE RULE
================================
If you cannot evaluate or explain:
- Set result to "error"
- Set feedback to "Assessment evaluation failed. Please retry."
- Do NOT return empty or incomplete responses

""" + JSON_OUTPUT_INSTRUCTION + """
Return ONLY a JSON object with these MANDATORY keys: 
- "is_correct": boolean (true if exact match with correct_answer),
- "result": "correct" | "incorrect" | "error",
- "marks": 0 or 1,
- "feedback": "MANDATORY explanation - CORRECT: 1-2 sentences. INCORRECT: 3-5 sentences with teaching.",
- "correct_explanation": "The correct answer and comprehensive explanation of why it is correct"
"""

QNA_EVALUATION_PROMPT = """Evaluate the user's answer to the question.

================================
CRITICAL ASSESSMENT ENFORCEMENT
================================
This evaluation MUST NOT fail silently. EVERY answer receives evaluation.

=== STEP 1: VALIDATION (MANDATORY) ===
First, check if the answer is MEANINGFUL TEXT:
- If EMPTY, RANDOM CHARACTERS, or GIBBERISH (no clear words/meaning):
  - Mark as INCORRECT immediately
  - Assign all scores = 0
  - Provide a DETAILED explanation of the correct answer

Examples of INVALID answers (score = 0):
- Empty or whitespace only
- "asdf", "asdfsadf", "xyz123", "!@#$%"
- Random letters: "jkl mno pqr"
- Copy of the question without answering

=== STEP 2: EVALUATION (only for valid answers) ===
Use this WORD-BASED RUBRIC:

1. Correctness (0-5 marks): Are the core concepts correct?
   - 5: All concepts accurate
   - 3-4: Most correct, minor errors
   - 1-2: Some correct but significant errors
   - 0: Wrong or no relevant content

2. Completeness (0-3 marks): Are key points covered for {length} mode?
   - 3: All key aspects covered
   - 2: Most key aspects covered
   - 1: Minimal coverage
   - 0: Key points missing

3. Clarity (0-2 marks): Is the answer understandable?
   - 2: Clear and well-structured
   - 1: Understandable but poorly organized
   - 0: Confusing or incoherent

=== STEP 3: SCORING & CLASSIFICATION ===
Total score = sum of rubric scores (0-10)

CLASSIFICATION (STRICT - NO "partial" category):
- Score >= 4 → "correct" (counts for mastery)
- Score < 4 → "incorrect" (does not count for mastery)

After this evaluation:
- questions_attempted += 1
- If score >= 4: correct_answers += 1
- mastery = correct_answers / questions_attempted
- mastery < 0.40 → WEAK, mastery >= 0.40 → STRONG

=== STEP 4: EXPLANATION GUARANTEE ===
FORBIDDEN to skip explanation. EVERY answer MUST receive:

- If CORRECT (score >= 4):
  SHORT explanation (1-2 sentences) confirming why answer is correct.

- If INCORRECT (score < 4):
  DETAILED explanation (3-5 sentences):
  1. What the CORRECT answer should be
  2. WHY it is correct
  3. What was MISSING or WRONG
  4. Address any MISCONCEPTIONS

=== FAILURE RULE ===
If you cannot evaluate: return result="error", feedback="Assessment evaluation failed. Please retry."

Topic: {topic}
Question: {question}
Expected Mode: {length}
Expected Answer Context: {context}
User Answer: {user_answer}

""" + JSON_OUTPUT_INSTRUCTION + """
Return ONLY a JSON object with these MANDATORY keys:
"is_valid_answer": boolean (false if gibberish/empty/random),
"result": "correct" | "incorrect" | "error",
"concept_score": int (0-5),
"completeness_score": int (0-3),
"clarity_score": int (0-2),
"total_marks": int (sum of scores, 0-10),
"feedback": "MANDATORY: CORRECT (score>=4): 1-2 sentences. INCORRECT (score<4): 3-5 sentences DETAILED.",
"rubric_evaluation": "brief breakdown of scores for each category",
"correct_explanation": "The COMPLETE correct answer with full explanation - ALWAYS provide"
"""

QNA_GENERATION_PROMPT = """Generate a question-answer (Q&A) challenge for the topic: {topic}.
Difficulty Level: {difficulty} (based on mastery score {mastery})
Desired Mode: {length} (Short, Medium, or Long)

Context:
{context}

Requirements:
1. One clear question that requires a {length} answer.
   - Short: Definition-level, 2–4 sentences expected.
   - Medium: Concept + explanation, Example encouraged.
   - Long: Concept + Explanation + Example + (Optional) limitations or use-cases.
2. The question should be thought-provoking and relevant to the context.

""" + JSON_OUTPUT_INSTRUCTION + """
Return ONLY a JSON object with keys: "question", "expected_points", "length".
Do not include any preamble or explanation.
"""

GAP_DETECTION_PROMPT = """Analyze the interaction to identify knowledge gaps and mastered concepts.
User message: {input}
AI response: {output}

Identify:
1. detected_gaps: concepts the user seems to struggle with.
2. mastered_concepts: concepts the user seems to understand well.
3. suggested_level: beginner, intermediate, or advanced based on the depth of the conversation.
"""
