import json
import math
from typing import List, Dict

class MatchingSystem:
    def __init__(self, db):
        self.db = db
    
    def calculate_match_percentage(self, vector1_str: str, vector2_str: str) -> float:
        vector1 = json.loads(vector1_str)
        vector2 = json.loads(vector2_str)
        
        if len(vector1) != len(vector2):
            return 0.0
        
        dot_product = sum(v1 * v2 for v1, v2 in zip(vector1, vector2))
        magnitude1 = math.sqrt(sum(v * v for v in vector1))
        magnitude2 = math.sqrt(sum(v * v for v in vector2))
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        cosine_similarity = dot_product / (magnitude1 * magnitude2)
        
        percentage = ((cosine_similarity + 1) / 2) * 100
        
        return round(percentage, 1)
    
    def calculate_all_matches_for_patient(self, patient_id: int):
        patient_vector = self.db.get_test_result(patient_id)
        if not patient_vector:
            return
        
        psychologists = self.db.get_all_psychologists()
        
        for psychologist_id in psychologists:
            psychologist_vector = self.db.get_test_result(psychologist_id)
            if psychologist_vector:
                match_percentage = self.calculate_match_percentage(
                    patient_vector, psychologist_vector
                )
                self.db.save_match(patient_id, psychologist_id, match_percentage)
    
    def calculate_all_matches_for_psychologist(self, psychologist_id: int):
        psychologist_vector = self.db.get_test_result(psychologist_id)
        if not psychologist_vector:
            return
        
        patients = self.db.get_all_patients()
        
        for patient_id in patients:
            patient_vector = self.db.get_test_result(patient_id)
            if patient_vector:
                match_percentage = self.calculate_match_percentage(
                    patient_vector, psychologist_vector
                )
                self.db.save_match(patient_id, psychologist_id, match_percentage)


class PsychologicalTest:
    def __init__(self, questions: List[Dict]):
        self.questions = questions
    
    def get_question(self, index: int) -> Dict:
        if 0 <= index < len(self.questions):
            return self.questions[index]
        return None
    
    def get_total_questions(self) -> int:
        return len(self.questions)
    
    def calculate_values_vector(self, answers: Dict[int, int]) -> str:
        num_dimensions = len(self.questions[0]['weights']) if self.questions else 0
        vector = [0.0] * num_dimensions
        
        for question_idx, answer_value in answers.items():
            if question_idx < len(self.questions):
                question = self.questions[question_idx]
                weights = question['weights']
                for i in range(len(weights)):
                    vector[i] += weights[i] * answer_value
        
        max_val = max(abs(v) for v in vector) if vector else 1
        if max_val > 0:
            vector = [v / max_val for v in vector]
        
        return json.dumps(vector)

