-- Example SQL file

-- Create a table
-- ALTER TABLE employees
-- ADD email varchar(50);

-- Insert data into the table
INSERT INTO USER_DETAILS (USER_ID, NAME)
VALUES (9, 'Kubhakarna-test');




-- CREATE OR REPLACE FUNCTION calculate_salary(employee_id NUMBER)
-- RETURN NUMBER
-- IS
--     v_salary NUMBER;
-- BEGIN
--     -- Retrieve the salary based on the given employee_id
--     SELECT salary INTO v_salary
--     FROM employees
--     WHERE employee_id = employee_id;

--     RETURN v_salary;
-- END;
-- /


-- SELECT employee_id, calculate_salary(employee_id) AS salary
-- FROM employees;

-- INSERT INTO employees (employee_id, first_name, last_name, hire_date, salary, department_id)
-- VALUES (8, 'Deepak', 'Pawar', TO_DATE('2023-02-01', 'YYYY-MM-DD'), 35000.00, 104);

-- Query the data
--SELECT * FROM employees;
