CREATE OR REPLACE PROCEDURE InsertEmployee(emp_name VARCHAR2, emp_salary NUMBER) IS
BEGIN
    INSERT INTO employees (FIRST_NAME, SALARY) VALUES (emp_name, emp_salary);
    COMMIT; -- You might need to commit explicitly in Oracle
EXCEPTION
    WHEN OTHERS THEN
        ROLLBACK; -- Handle exceptions and perform rollback if necessary
        RAISE; -- Reraise the exception for further handling
END;
