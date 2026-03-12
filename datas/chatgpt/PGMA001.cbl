       IDENTIFICATION DIVISION.
       PROGRAM-ID. PGMA001.

       ENVIRONMENT DIVISION.

       DATA DIVISION.
       WORKING-STORAGE SECTION.

       77  WS-PGM-NAME                 PIC X(08) VALUE 'PGMA001'.
       77  WS-SQLCODE-DISPLAY          PIC -9(09).
       77  WS-TMP-COUNT                PIC 9(05) VALUE 0.
       77  WS-CALC-AMT                 PIC S9(11)V99 COMP-3 VALUE 0.
       77  WS-CALC-FEE                 PIC S9(09)V99 COMP-3 VALUE 0.
       77  WS-CALC-TOTAL               PIC S9(11)V99 COMP-3 VALUE 0.
       77  WS-RETRY-COUNT              PIC 9(01) VALUE 0.

       01  WS-SWITCHES.
           05  WS-END-PROCESS          PIC X VALUE 'N'.
               88  END-PROCESS               VALUE 'Y'.
               88  CONTINUE-PROCESS          VALUE 'N'.
           05  WS-SQL-ERROR            PIC X VALUE 'N'.
               88  SQL-ERROR                 VALUE 'Y'.
               88  SQL-OK                    VALUE 'N'.

       EXEC SQL
            INCLUDE SQLCA
       END-EXEC.

       LINKAGE SECTION.
       01  LK-PROGRAM-NAME             PIC X(08).
       COPY CPYBATCH.

       PROCEDURE DIVISION USING LK-PROGRAM-NAME
                                CPYB-BATCH-CONTEXT.

       0000-MAIN.
           PERFORM 1000-INIT THRU 1000-EXIT
           PERFORM 2000-VALIDATE THRU 2000-EXIT
           IF CPYB-VALIDATION-KO
              PERFORM 9000-FINALIZE THRU 9000-EXIT
              GOBACK
           END-IF

           PERFORM 3000-BUSINESS-DISPATCH THRU 3000-EXIT
           PERFORM 9000-FINALIZE THRU 9000-EXIT
           GOBACK
           .

       1000-INIT.
           MOVE SPACES                 TO CPYB-ERR-CODE
                                          CPYB-ERR-MSG
                                          CPYB-DB-INFO
                                          CPYB-PGM-RETURN
           MOVE ZERO                   TO WS-CALC-AMT
                                          WS-CALC-FEE
                                          WS-CALC-TOTAL
           MOVE SQLCODE                TO WS-SQLCODE-DISPLAY
           SET SQL-OK                  TO TRUE
           SET CONTINUE-PROCESS        TO TRUE

           IF CPYB-AMOUNT > 10000
              SET CPYB-HIGH-AMOUNT     TO TRUE
           ELSE
              SET CPYB-NOT-HIGH-AMOUNT TO TRUE
           END-IF

           IF CPYB-COUNTRY NOT = 'FRA'
              SET CPYB-FOREIGN-REQUEST TO TRUE
           ELSE
              SET CPYB-DOMESTIC-REQUEST TO TRUE
           END-IF
           .

       1000-EXIT.
           EXIT
           .

       2000-VALIDATE.
           IF CPYB-CLIENT-ID = SPACES
              MOVE 'V001' TO CPYB-ERR-CODE
              MOVE 'CLIENT ID MISSING' TO CPYB-ERR-MSG
              SET CPYB-VALIDATION-KO TO TRUE
           ELSE
              IF CPYB-ACCOUNT-ID = SPACES
                 MOVE 'V002' TO CPYB-ERR-CODE
                 MOVE 'ACCOUNT ID MISSING' TO CPYB-ERR-MSG
                 SET CPYB-VALIDATION-KO TO TRUE
              ELSE
                 IF CPYB-ACTION-CODE = 'PY'
                    OR CPYB-ACTION-CODE = 'RF'
                    OR CPYB-ACTION-CODE = 'BL'
                    SET CPYB-VALIDATION-OK TO TRUE
                 ELSE
                    MOVE 'V003' TO CPYB-ERR-CODE
                    MOVE 'UNSUPPORTED ACTION CODE' TO CPYB-ERR-MSG
                    SET CPYB-VALIDATION-KO TO TRUE
                 END-IF
              END-IF
           END-IF
           .

       2000-EXIT.
           EXIT
           .

       3000-BUSINESS-DISPATCH.
           EVALUATE CPYB-ACTION-CODE
              WHEN 'PY'
                 PERFORM 3100-LOAD-ACCOUNT THRU 3100-EXIT
                 PERFORM 3200-CHECK-CLIENT THRU 3200-EXIT
                 PERFORM 3300-CALCULATE-PAYMENT THRU 3300-EXIT
                 PERFORM 3400-PERSIST-PAYMENT THRU 3400-EXIT
              WHEN 'RF'
                 PERFORM 3500-LOAD-REFUND THRU 3500-EXIT
                 PERFORM 3600-PERSIST-REFUND THRU 3600-EXIT
              WHEN 'BL'
                 PERFORM 3200-CHECK-CLIENT THRU 3200-EXIT
                 PERFORM 3700-BLOCK-ACCOUNT THRU 3700-EXIT
              WHEN OTHER
                 MOVE 'B999' TO CPYB-ERR-CODE
                 MOVE 'UNKNOWN BUSINESS ACTION' TO CPYB-ERR-MSG
           END-EVALUATE
           .

       3000-EXIT.
           EXIT
           .

       3100-LOAD-ACCOUNT.
           SET CPYB-SQL-NEEDED TO TRUE

           EXEC SQL
                SELECT ACCOUNT_STATUS,
                       ROUTING_CODE
                  INTO :CPYB-STATUS,
                       :CPYB-ROUTING-CODE
                  FROM T_ACCOUNT
                 WHERE ACCOUNT_ID = :CPYB-ACCOUNT-ID
           END-EXEC

           MOVE SQLCODE TO WS-SQLCODE-DISPLAY

           IF SQLCODE = 0
              SET CPYB-ACCOUNT-FOUND TO TRUE
              MOVE 'ACCOUNT FOUND' TO CPYB-DB-INFO
           ELSE
              IF SQLCODE = 100
                 SET CPYB-ACCOUNT-NOT-FOUND TO TRUE
                 MOVE 'S404' TO CPYB-ERR-CODE
                 MOVE 'ACCOUNT NOT FOUND' TO CPYB-ERR-MSG
              ELSE
                 SET SQL-ERROR TO TRUE
                 MOVE 'S500' TO CPYB-ERR-CODE
                 MOVE 'SQL ERROR ON ACCOUNT SELECT' TO CPYB-ERR-MSG
              END-IF
           END-IF
           .

       3100-EXIT.
           EXIT
           .

       3200-CHECK-CLIENT.
           EXEC SQL
                SELECT BLOCKED_FLAG,
                       SEGMENT,
                       RISK_LEVEL
                  INTO :CPYB-FLG-CLIENT-BLOCKED,
                       :CPYB-SEGMENT,
                       :CPYB-RISK-LEVEL
                  FROM T_CLIENT
                 WHERE CLIENT_ID = :CPYB-CLIENT-ID
           END-EXEC

           MOVE SQLCODE TO WS-SQLCODE-DISPLAY

           IF SQLCODE NOT = 0
              IF SQLCODE = 100
                 MOVE 'S405' TO CPYB-ERR-CODE
                 MOVE 'CLIENT NOT FOUND' TO CPYB-ERR-MSG
              ELSE
                 MOVE 'S501' TO CPYB-ERR-CODE
                 MOVE 'SQL ERROR ON CLIENT SELECT' TO CPYB-ERR-MSG
              END-IF
           ELSE
              EVALUATE TRUE
                 WHEN CPYB-CLIENT-BLOCKED
                    MOVE 'BLOC' TO CPYB-DECISION-CODE
                    SET CPYB-MANUAL-REVIEW TO TRUE
                 WHEN CPYB-RISK-LEVEL >= 7
                    MOVE 'RISK' TO CPYB-DECISION-CODE
                    SET CPYB-MANUAL-REVIEW TO TRUE
                 WHEN OTHER
                    MOVE 'AUTO' TO CPYB-DECISION-CODE
                    SET CPYB-AUTO-REVIEW TO TRUE
              END-EVALUATE
           END-IF
           .

       3200-EXIT.
           EXIT
           .

       3300-CALCULATE-PAYMENT.
           MOVE CPYB-AMOUNT TO WS-CALC-AMT

           IF CPYB-SEGMENT = 'PR'
              COMPUTE WS-CALC-FEE = CPYB-AMOUNT * 0.015
           ELSE
              IF CPYB-SEGMENT = 'CO'
                 COMPUTE WS-CALC-FEE = CPYB-AMOUNT * 0.010
              ELSE
                 COMPUTE WS-CALC-FEE = CPYB-AMOUNT * 0.020
              END-IF
           END-IF

           IF CPYB-HIGH-AMOUNT
              COMPUTE WS-CALC-FEE = WS-CALC-FEE + 15
           ELSE
              CONTINUE
           END-IF

           IF CPYB-FOREIGN-REQUEST
              COMPUTE WS-CALC-FEE = WS-CALC-FEE + 25
           ELSE
              CONTINUE
           END-IF

           COMPUTE WS-CALC-TOTAL = WS-CALC-AMT + WS-CALC-FEE

           MOVE WS-CALC-FEE   TO CPYB-FEE
           MOVE WS-CALC-TOTAL TO CPYB-TOTAL

           EVALUATE TRUE
              WHEN CPYB-CLIENT-BLOCKED
                 MOVE 'RJ' TO CPYB-DECISION-CODE
              WHEN CPYB-MANUAL-REVIEW
                 MOVE 'RV' TO CPYB-DECISION-CODE
              WHEN CPYB-ACCOUNT-NOT-FOUND
                 MOVE 'KO' TO CPYB-DECISION-CODE
              WHEN OTHER
                 MOVE 'OK' TO CPYB-DECISION-CODE
           END-EVALUATE
           .

       3300-EXIT.
           EXIT
           .

       3400-PERSIST-PAYMENT.
           IF CPYB-DECISION-CODE = 'OK'
              EXEC SQL
                   INSERT INTO T_PAYMENT
                   (REQ_ID,
                    CLIENT_ID,
                    ACCOUNT_ID,
                    AMOUNT,
                    FEE,
                    TOTAL,
                    DECISION_CODE,
                    PROCESS_DATE)
                   VALUES
                   (:CPYB-REQ-ID,
                    :CPYB-CLIENT-ID,
                    :CPYB-ACCOUNT-ID,
                    :CPYB-AMOUNT,
                    :CPYB-FEE,
                    :CPYB-TOTAL,
                    :CPYB-DECISION-CODE,
                    :CPYB-PROCESS-DATE)
              END-EXEC

              IF SQLCODE NOT = 0
                 MOVE 'S601' TO CPYB-ERR-CODE
                 MOVE 'INSERT PAYMENT FAILED' TO CPYB-ERR-MSG
              ELSE
                 MOVE '0000' TO CPYB-PGM-RETURN
              END-IF
           ELSE
              EXEC SQL
                   INSERT INTO T_PAYMENT_AUDIT
                   (REQ_ID,
                    DECISION_CODE,
                    ERROR_CODE,
                    ERROR_MSG)
                   VALUES
                   (:CPYB-REQ-ID,
                    :CPYB-DECISION-CODE,
                    :CPYB-ERR-CODE,
                    :CPYB-ERR-MSG)
              END-EXEC

              IF SQLCODE = 0
                 MOVE '1001' TO CPYB-PGM-RETURN
              ELSE
                 MOVE 'S602' TO CPYB-ERR-CODE
                 MOVE 'INSERT PAYMENT AUDIT FAILED' TO CPYB-ERR-MSG
              END-IF
           END-IF
           .

       3400-EXIT.
           EXIT
           .

       3500-LOAD-REFUND.
           EXEC SQL
                SELECT COUNT(*)
                  INTO :WS-TMP-COUNT
                  FROM T_PAYMENT
                 WHERE REQ_ID = :CPYB-REQ-ID
           END-EXEC

           IF SQLCODE = 0
              IF WS-TMP-COUNT > 0
                 MOVE 'RFOK' TO CPYB-DECISION-CODE
              ELSE
                 MOVE 'RFKO' TO CPYB-DECISION-CODE
                 MOVE 'R404' TO CPYB-ERR-CODE
                 MOVE 'PAYMENT NOT FOUND FOR REFUND' TO CPYB-ERR-MSG
              END-IF
           ELSE
              MOVE 'R500' TO CPYB-ERR-CODE
              MOVE 'SQL ERROR ON REFUND CHECK' TO CPYB-ERR-MSG
           END-IF
           .

       3500-EXIT.
           EXIT
           .

       3600-PERSIST-REFUND.
           IF CPYB-DECISION-CODE = 'RFOK'
              EXEC SQL
                   INSERT INTO T_REFUND
                   (REQ_ID,
                    CLIENT_ID,
                    ACCOUNT_ID,
                    AMOUNT,
                    PROCESS_DATE)
                   VALUES
                   (:CPYB-REQ-ID,
                    :CPYB-CLIENT-ID,
                    :CPYB-ACCOUNT-ID,
                    :CPYB-AMOUNT,
                    :CPYB-PROCESS-DATE)
              END-EXEC

              IF SQLCODE = 0
                 MOVE '0000' TO CPYB-PGM-RETURN
              ELSE
                 MOVE 'R601' TO CPYB-ERR-CODE
                 MOVE 'INSERT REFUND FAILED' TO CPYB-ERR-MSG
              END-IF
           ELSE
              MOVE '1002' TO CPYB-PGM-RETURN
           END-IF
           .

       3600-EXIT.
           EXIT
           .

       3700-BLOCK-ACCOUNT.
           IF CPYB-CLIENT-BLOCKED
              EXEC SQL
                   UPDATE T_ACCOUNT
                      SET ACCOUNT_STATUS = 'BL'
                    WHERE ACCOUNT_ID = :CPYB-ACCOUNT-ID
              END-EXEC

              IF SQLCODE = 0
                 MOVE 'BLKD' TO CPYB-DECISION-CODE
                 MOVE '0000' TO CPYB-PGM-RETURN
              ELSE
                 MOVE 'B601' TO CPYB-ERR-CODE
                 MOVE 'ACCOUNT BLOCK UPDATE FAILED' TO CPYB-ERR-MSG
              END-IF
           ELSE
              MOVE 'B010' TO CPYB-ERR-CODE
              MOVE 'CLIENT NOT BLOCKED, NO ACCOUNT UPDATE' TO CPYB-ERR-MSG
              MOVE '1003' TO CPYB-PGM-RETURN
           END-IF
           .

       3700-EXIT.
           EXIT
           .

       9000-FINALIZE.
           EVALUATE TRUE
              WHEN CPYB-ERR-CODE = SPACES
                 CONTINUE
              WHEN CPYB-PGM-RETURN = SPACES
                 MOVE '9999' TO CPYB-PGM-RETURN
              WHEN OTHER
                 CONTINUE
           END-EVALUATE
           .

       9000-EXIT.
           EXIT
           .