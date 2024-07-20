import numpy as np
import nltk as nlp
import openai
import os


class SubjectiveQuestions:

    def __init__(self, data):
        self.summary = data
        #openai.api_key = 'removed for safety'

    def generate_test(self):
        prompt = (
            f"Generate between 10 to 30 subjective questions and answers from the following text:\n\n"
            f"{self.summary}\n\n"
            "Output the questions and answers in the following format:\n"
            "Q: <question>\nA: <answer>\n\n"
        )
        response = openai.Completion.create(
            engine="gpt-3.5-turbo-instruct",
            prompt=prompt,
            max_tokens=1000,
            n=1,
            stop=None,
            temperature=0.7,
        )
        generated_text = response['choices'][0]['text'].strip()
        questions_and_answers = generated_text.split("\n\n")

        questions = []
        answers = []
        for qa in questions_and_answers:
            if "Q: " in qa and "A: " in qa:
                question, answer = qa.split("A: ", 1)
                question = question.replace("Q: ", "")
                questions.append(question.strip())
                answers.append(answer.strip())

        return questions, answers