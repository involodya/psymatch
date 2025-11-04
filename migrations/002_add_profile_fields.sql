-- Migration 002: Добавление новых полей в профиль психолога (v2.0)

-- Добавляем новые поля в psychologist_profiles
ALTER TABLE psychologist_profiles ADD COLUMN gender TEXT;
ALTER TABLE psychologist_profiles ADD COLUMN age INTEGER;
ALTER TABLE psychologist_profiles ADD COLUMN about_me TEXT;
ALTER TABLE psychologist_profiles ADD COLUMN approach TEXT;
ALTER TABLE psychologist_profiles ADD COLUMN work_requests TEXT;
ALTER TABLE psychologist_profiles ADD COLUMN price TEXT;

