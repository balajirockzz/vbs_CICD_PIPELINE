-- Example SQL file

-- Create a table
--ALTER TABLE employees
--ADD Age INTEGER(2);

-- Insert data into the table
INSERT INTO employees (employee_id, first_name, last_name, hire_date, salary, department_id)
VALUES (3, 'Pankaj', 'Dhumal', TO_DATE('2023-01-04', 'YYYY-MM-DD'), 8000.00, 103);

--INSERT INTO employees (employee_id, first_name, last_name, hire_date, salary, department_id)
--VALUES (5, 'Sujit', 'Patil', TO_DATE('2023-02-01', 'YYYY-MM-DD'), 9000.00, 104);

-- Query the data
--SELECT * FROM employees;