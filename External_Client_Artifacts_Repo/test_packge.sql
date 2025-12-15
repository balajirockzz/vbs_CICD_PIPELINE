CREATE OR REPLACE PACKAGE MathPackage IS
    FUNCTION CalculateSquare(input_number IN NUMBER) RETURN NUMBER;
    PROCEDURE PrintMessage(message IN VARCHAR2);
END MathPackage;

/ 

CREATE OR REPLACE PACKAGE BODY MathPackage IS
    FUNCTION CalculateSquare(input_number IN NUMBER) RETURN NUMBER IS
        result NUMBER;
    BEGIN
        result := input_number * input_number;
        RETURN result;
    END CalculateSquare;
 
    PROCEDURE PrintMessage(message IN VARCHAR2) IS
    BEGIN
        DBMS_OUTPUT.PUT_LINE(message);
    END PrintMessage;
END MathPackage;

/

COMMIT;