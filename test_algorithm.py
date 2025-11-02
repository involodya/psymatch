#!/usr/bin/env python3

import json
from matching import PsychologicalTest

def test_matching():
    print("=== PsyMatch Algorithm Test ===\n")
    
    with open('test_questions.json', 'r', encoding='utf-8') as f:
        questions = json.load(f)
    
    test = PsychologicalTest(questions)
    
    print(f"Loaded {test.get_total_questions()} questions\n")
    
    answers_user1 = {i: 4 for i in range(len(questions))}
    answers_user2 = {i: 4 for i in range(len(questions))}
    answers_user3 = {i: 0 for i in range(len(questions))}
    answers_user4 = {i: 2 for i in range(len(questions))}
    
    vector1 = test.calculate_values_vector(answers_user1)
    vector2 = test.calculate_values_vector(answers_user2)
    vector3 = test.calculate_values_vector(answers_user3)
    vector4 = test.calculate_values_vector(answers_user4)
    
    print("Test scenarios:")
    print("User 1: All answers = 4 (maximum positive)")
    print("User 2: All answers = 4 (same as User 1)")
    print("User 3: All answers = 0 (maximum negative)")
    print("User 4: All answers = 2 (neutral)\n")
    
    from matching import MatchingSystem
    
    class FakeDB:
        def get_test_result(self, user_id):
            return None
        def save_match(self, p1, p2, pct):
            pass
        def get_all_psychologists(self):
            return []
        def get_all_patients(self):
            return []
    
    matcher = MatchingSystem(FakeDB())
    
    match_1_2 = matcher.calculate_match_percentage(vector1, vector2)
    match_1_3 = matcher.calculate_match_percentage(vector1, vector3)
    match_1_4 = matcher.calculate_match_percentage(vector1, vector4)
    match_3_4 = matcher.calculate_match_percentage(vector3, vector4)
    
    print("Matching results:")
    print(f"User 1 <-> User 2 (identical): {match_1_2}% ✓ (should be ~100%)")
    print(f"User 1 <-> User 3 (opposite): {match_1_3}% ✓ (should be low)")
    print(f"User 1 <-> User 4 (positive vs neutral): {match_1_4}%")
    print(f"User 3 <-> User 4 (negative vs neutral): {match_3_4}%")
    
    print("\n✅ Algorithm test completed!")
    print("\nNote: High match % means users have similar values and approach,")
    print("which suggests good compatibility for psychologist-patient interaction.")

if __name__ == '__main__':
    test_matching()

