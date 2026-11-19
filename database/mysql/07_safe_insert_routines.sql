USE electoraw;

-- These routines are informational only. They do not reject or update rows.
DROP FUNCTION IF EXISTS fn_electoraw_insert_normalize;
CREATE FUNCTION fn_electoraw_insert_normalize(value VARCHAR(255))
RETURNS VARCHAR(255)
DETERMINISTIC
NO SQL
RETURN LOWER(TRIM(COALESCE(value, '')));

DROP FUNCTION IF EXISTS fn_electoraw_insert_age_eligible;
CREATE FUNCTION fn_electoraw_insert_age_eligible(candidate_age DECIMAL(5,2))
RETURNS TINYINT
DETERMINISTIC
NO SQL
RETURN IF(candidate_age IS NOT NULL AND candidate_age >= 25, 1, 0);

-- Future registrations only: write an audit event after a successful insert.
-- Existing users are untouched and invalid legacy data is not rejected.
DROP TRIGGER IF EXISTS trg_workflow_users_ai_audit;
CREATE TRIGGER trg_workflow_users_ai_audit
AFTER INSERT ON workflow_users
FOR EACH ROW
INSERT IGNORE INTO workflow_audit_log
    (id, user_id, action, entity_type, entity_id, details_json, created_at)
VALUES
    (CONCAT('insert_audit_', UUID()), NEW.id,
     'user_registered', 'workflow_user', NEW.id,
     JSON_OBJECT('normalized_email', fn_electoraw_insert_normalize(NEW.email)),
     CURRENT_TIMESTAMP(6));

-- Future nominations only: write an audit event after a successful insert.
-- This trigger does not alter status, age, winner state, or form data.
DROP TRIGGER IF EXISTS trg_workflow_nominations_ai_audit_safe;
CREATE TRIGGER trg_workflow_nominations_ai_audit_safe
AFTER INSERT ON workflow_nominations
FOR EACH ROW
INSERT IGNORE INTO workflow_audit_log
    (id, user_id, action, entity_type, entity_id, details_json, created_at)
VALUES
    (CONCAT('insert_audit_', UUID()), NEW.candidate_user_id,
     'nomination_created', 'nomination', NEW.id,
     JSON_OBJECT(
         'state', NEW.state,
         'constituency', NEW.constituency,
         'age_eligible',
         fn_electoraw_insert_age_eligible(
             CAST(NULLIF(JSON_UNQUOTE(JSON_EXTRACT(NEW.form_json, '$.age')), '') AS DECIMAL(5,2))
         )
     ),
     CURRENT_TIMESTAMP(6));
