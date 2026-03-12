       IDENTIFICATION DIVISION.
       PROGRAM-ID. PGMB001.

       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT IN-FILE ASSIGN TO 'INPUTB.DAT'
               ORGANIZATION IS LINE SEQUENTIAL
               FILE STATUS IS WS-INFILE-STATUS.

       DATA DIVISION.
       FILE SECTION.
       FD  IN-FILE
           RECORD CONTAINS 120 CHARACTERS
           BLOCK CONTAINS 0 RECORDS.
       01  IN-REC                        PIC X(120).

       WORKING-STORAGE SECTION.

       77  WS-PGM-NAME                  PIC X(08) VALUE 'PGMA001'.
       77  WS-INFILE-STATUS             PIC XX VALUE SPACES.
       77  WS-EOF-SW                    PIC X VALUE 'N'.
           88  EOF-REACHED                    VALUE 'Y'.
           88  EOF-NOT-REACHED                VALUE 'N'.
       77  WS-LINE-NBR                  PIC 9(07) VALUE 0.
       77  WS-PROCESSED-NBR             PIC 9(07) VALUE 0.
       77  WS-ERROR-NBR                 PIC 9(07) VALUE 0.
       77  WS-SUB                       PIC 9(03) VALUE 0.

       01  WS-PARSE-AREA.
           05  WS-F-REQ-ID              PIC X(12).
           05  WS-F-CLIENT-ID           PIC X(10).
           05  WS-F-ACCOUNT-ID          PIC X(12).
           05  WS-F-ACTION              PIC X(02).
           05  WS-F-CHANNEL             PIC X(03).
           05  WS-F-COUNTRY             PIC X(03).
           05  WS-F-CURRENCY            PIC X(03).
           05  WS-F-AMOUNT              PIC X(11).
           05  WS-F-PRIORITY            PIC X(01).
           05  WS-F-PRODUCT             PIC X(04).
           05  WS-F-FILLER              PIC X(61).

       01  WS-AMOUNTS.
           05  WS-AMOUNT-N              PIC 9(9)V99 VALUE 0.
           05  WS-DEFAULT-FEE           PIC 9(5)V99 VALUE 0.
           05  WS-WORK-TOTAL            PIC 9(9)V99 VALUE 0.

       01  WS-FLAGS.
           05  WS-VALID-RECORD          PIC X VALUE 'N'.
               88  VALID-RECORD               VALUE 'Y'.
               88  INVALID-RECORD             VALUE 'N'.
           05  WS-CALL-REQUIRED         PIC X VALUE 'N'.
               88  CALL-REQUIRED              VALUE 'Y'.
               88  CALL-NOT-REQUIRED          VALUE 'N'.
           05  WS-HIGH-PRIORITY         PIC X VALUE 'N'.
               88  HIGH-PRIORITY              VALUE 'Y'.
               88  NORMAL-PRIORITY            VALUE 'N'.

       COPY CPYBATCH.

       PROCEDURE DIVISION.

       0000-MAIN.
           PERFORM 1000-INIT THRU 1000-EXIT
           PERFORM 2000-OPEN-FILE THRU 2000-EXIT

           IF WS-INFILE-STATUS NOT = '00'
              DISPLAY 'ERROR OPEN INPUT FILE, STATUS=' WS-INFILE-STATUS
              GOBACK
           END-IF

           PERFORM 3000-READ-LOOP THRU 3000-EXIT
               UNTIL EOF-REACHED

           PERFORM 9000-END THRU 9000-EXIT
           GOBACK
           .

       1000-INIT.
           MOVE ZERO                    TO WS-LINE-NBR
                                          WS-PROCESSED-NBR
                                          WS-ERROR-NBR
                                          WS-AMOUNT-N
                                          WS-DEFAULT-FEE
                                          WS-WORK-TOTAL
           SET EOF-NOT-REACHED         TO TRUE
           SET INVALID-RECORD          TO TRUE
           SET CALL-NOT-REQUIRED       TO TRUE
           SET NORMAL-PRIORITY         TO TRUE
           .

       1000-EXIT.
           EXIT
           .

       2000-OPEN-FILE.
           OPEN INPUT IN-FILE
           .

       2000-EXIT.
           EXIT
           .

       3000-READ-LOOP.
           READ IN-FILE
              AT END
                 SET EOF-REACHED TO TRUE
              NOT AT END
                 ADD 1 TO WS-LINE-NBR
                 PERFORM 3100-CLEAR-CONTEXT THRU 3100-EXIT
                 PERFORM 3200-PARSE-RECORD THRU 3200-EXIT
                 PERFORM 3300-VALIDATE-RECORD THRU 3300-EXIT
                 PERFORM 3400-DECIDE-ACTION THRU 3400-EXIT
                 PERFORM 3500-OPTIONAL-CALL THRU 3500-EXIT
           END-READ
           .

       3000-EXIT.
           EXIT
           .

       3100-CLEAR-CONTEXT.
           MOVE SPACES TO WS-F-REQ-ID
                          WS-F-CLIENT-ID
                          WS-F-ACCOUNT-ID
                          WS-F-ACTION
                          WS-F-CHANNEL
                          WS-F-COUNTRY
                          WS-F-CURRENCY
                          WS-F-AMOUNT
                          WS-F-PRIORITY
                          WS-F-PRODUCT
                          WS-F-FILLER
                          CPYB-REQ-ID
                          CPYB-CLIENT-ID
                          CPYB-ACCOUNT-ID
                          CPYB-ACTION-CODE
                          CPYB-CHANNEL
                          CPYB-COUNTRY
                          CPYB-CURRENCY
                          CPYB-STATUS
                          CPYB-SEGMENT
                          CPYB-PRODUCT
                          CPYB-DECISION-CODE
                          CPYB-ERR-CODE
                          CPYB-ERR-MSG
                          CPYB-DB-INFO
                          CPYB-ROUTING-CODE
                          CPYB-PGM-RETURN
                          CPYB-TRACE-ID

           MOVE ZERO   TO CPYB-AMOUNT
                          CPYB-FEE
                          CPYB-TOTAL
                          CPYB-PRIORITY
                          CPYB-RISK-LEVEL
                          WS-AMOUNT-N
                          WS-DEFAULT-FEE
                          WS-WORK-TOTAL

           SET CPYB-VALIDATION-KO      TO TRUE
           SET CPYB-SQL-NOT-NEEDED     TO TRUE
           SET CPYB-NOT-HIGH-AMOUNT    TO TRUE
           SET CPYB-DOMESTIC-REQUEST   TO TRUE
           SET CPYB-ACCOUNT-NOT-FOUND  TO TRUE
           SET CPYB-CLIENT-NOT-BLOCKED TO TRUE
           SET CPYB-AUTO-REVIEW        TO TRUE
           SET INVALID-RECORD          TO TRUE
           SET CALL-NOT-REQUIRED       TO TRUE
           .

       3100-EXIT.
           EXIT
           .

       3200-PARSE-RECORD.
           MOVE IN-REC(1:12)   TO WS-F-REQ-ID
           MOVE IN-REC(13:10)  TO WS-F-CLIENT-ID
           MOVE IN-REC(23:12)  TO WS-F-ACCOUNT-ID
           MOVE IN-REC(35:2)   TO WS-F-ACTION
           MOVE IN-REC(37:3)   TO WS-F-CHANNEL
           MOVE IN-REC(40:3)   TO WS-F-COUNTRY
           MOVE IN-REC(43:3)   TO WS-F-CURRENCY
           MOVE IN-REC(46:11)  TO WS-F-AMOUNT
           MOVE IN-REC(57:1)   TO WS-F-PRIORITY
           MOVE IN-REC(58:4)   TO WS-F-PRODUCT
           MOVE IN-REC(60:61)  TO WS-F-FILLER

           MOVE WS-F-REQ-ID      TO CPYB-REQ-ID
           MOVE WS-F-CLIENT-ID   TO CPYB-CLIENT-ID
           MOVE WS-F-ACCOUNT-ID  TO CPYB-ACCOUNT-ID
           MOVE WS-F-ACTION      TO CPYB-ACTION-CODE
           MOVE WS-F-CHANNEL     TO CPYB-CHANNEL
           MOVE WS-F-COUNTRY     TO CPYB-COUNTRY
           MOVE WS-F-CURRENCY    TO CPYB-CURRENCY
           MOVE WS-F-PRODUCT     TO CPYB-PRODUCT

           IF WS-F-AMOUNT NUMERIC
              MOVE WS-F-AMOUNT TO WS-AMOUNT-N
              MOVE WS-AMOUNT-N TO CPYB-AMOUNT
           ELSE
              MOVE 'P001' TO CPYB-ERR-CODE
              MOVE 'AMOUNT IS NOT NUMERIC' TO CPYB-ERR-MSG
           END-IF

           IF WS-F-PRIORITY NUMERIC
              MOVE WS-F-PRIORITY TO CPYB-PRIORITY
           ELSE
              MOVE 0 TO CPYB-PRIORITY
           END-IF

           MOVE 'BATCHUSR' TO CPYB-CREATED-BY
           MOVE '2026-03-09-12.00.00.000000' TO CPYB-CREATED-TS
           MOVE 'BATCHUSR' TO CPYB-UPDATED-BY
           MOVE '2026-03-09-12.00.00.000000' TO CPYB-UPDATED-TS
           MOVE 'TRACE000000000001' TO CPYB-TRACE-ID
           MOVE 20260309 TO CPYB-PROCESS-DATE
           .

       3200-EXIT.
           EXIT
           .

       3300-VALIDATE-RECORD.
           IF CPYB-REQ-ID = SPACES
              MOVE 'V101' TO CPYB-ERR-CODE
              MOVE 'REQ ID MISSING IN INPUT FILE' TO CPYB-ERR-MSG
              SET INVALID-RECORD TO TRUE
           ELSE
              IF CPYB-CLIENT-ID = SPACES
                 MOVE 'V102' TO CPYB-ERR-CODE
                 MOVE 'CLIENT ID MISSING IN INPUT FILE' TO CPYB-ERR-MSG
                 SET INVALID-RECORD TO TRUE
              ELSE
                 IF CPYB-ACTION-CODE = 'PY'
                    OR CPYB-ACTION-CODE = 'RF'
                    OR CPYB-ACTION-CODE = 'BL'
                    SET VALID-RECORD TO TRUE
                    SET CPYB-VALIDATION-OK TO TRUE
                 ELSE
                    MOVE 'V103' TO CPYB-ERR-CODE
                    MOVE 'INVALID ACTION CODE IN INPUT FILE' TO
                         CPYB-ERR-MSG
                    SET INVALID-RECORD TO TRUE
                 END-IF
              END-IF
           END-IF

           IF VALID-RECORD
              IF CPYB-PRIORITY >= 8
                 SET HIGH-PRIORITY TO TRUE
              ELSE
                 SET NORMAL-PRIORITY TO TRUE
              END-IF
           END-IF
           .

       3300-EXIT.
           EXIT
           .

       3400-DECIDE-ACTION.
           IF INVALID-RECORD
              ADD 1 TO WS-ERROR-NBR
              SET CALL-NOT-REQUIRED TO TRUE
           ELSE
              COMPUTE WS-DEFAULT-FEE = CPYB-AMOUNT * 0.01
              COMPUTE WS-WORK-TOTAL  = CPYB-AMOUNT + WS-DEFAULT-FEE

              MOVE WS-DEFAULT-FEE TO CPYB-FEE
              MOVE WS-WORK-TOTAL  TO CPYB-TOTAL

              IF CPYB-AMOUNT > 5000
                 SET CPYB-HIGH-AMOUNT TO TRUE
              ELSE
                 SET CPYB-NOT-HIGH-AMOUNT TO TRUE
              END-IF

              IF CPYB-COUNTRY NOT = 'FRA'
                 SET CPYB-FOREIGN-REQUEST TO TRUE
              ELSE
                 SET CPYB-DOMESTIC-REQUEST TO TRUE
              END-IF

              EVALUATE CPYB-ACTION-CODE
                 WHEN 'PY'
                    IF CPYB-AMOUNT > 0
                       IF HIGH-PRIORITY
                          SET CALL-REQUIRED TO TRUE
                          MOVE 'PY01' TO CPYB-DECISION-CODE
                       ELSE
                          IF CPYB-AMOUNT > 100
                             SET CALL-REQUIRED TO TRUE
                             MOVE 'PY02' TO CPYB-DECISION-CODE
                          ELSE
                             SET CALL-NOT-REQUIRED TO TRUE
                             MOVE 'PY03' TO CPYB-DECISION-CODE
                          END-IF
                       END-IF
                    ELSE
                       SET CALL-NOT-REQUIRED TO TRUE
                       MOVE 'P201' TO CPYB-ERR-CODE
                       MOVE 'PAYMENT AMOUNT <= 0' TO CPYB-ERR-MSG
                    END-IF

                 WHEN 'RF'
                    IF CPYB-AMOUNT > 0
                       SET CALL-REQUIRED TO TRUE
                       MOVE 'RF01' TO CPYB-DECISION-CODE
                    ELSE
                       SET CALL-NOT-REQUIRED TO TRUE
                       MOVE 'R201' TO CPYB-ERR-CODE
                       MOVE 'REFUND AMOUNT <= 0' TO CPYB-ERR-MSG
                    END-IF

                 WHEN 'BL'
                    IF CPYB-COUNTRY = 'FRA'
                       SET CALL-REQUIRED TO TRUE
                       MOVE 'BL01' TO CPYB-DECISION-CODE
                    ELSE
                       IF HIGH-PRIORITY
                          SET CALL-REQUIRED TO TRUE
                          MOVE 'BL02' TO CPYB-DECISION-CODE
                       ELSE
                          SET CALL-NOT-REQUIRED TO TRUE
                          MOVE 'B201' TO CPYB-ERR-CODE
                          MOVE 'FOREIGN LOW PRIORITY BLOCK IGNORED' TO
                               CPYB-ERR-MSG
                       END-IF
                    END-IF

                 WHEN OTHER
                    SET CALL-NOT-REQUIRED TO TRUE
                    MOVE 'X201' TO CPYB-ERR-CODE
                    MOVE 'NO ROUTING RULE FOR ACTION' TO CPYB-ERR-MSG
              END-EVALUATE
           END-IF
           .

       3400-EXIT.
           EXIT
           .

       3500-OPTIONAL-CALL.
           IF CALL-REQUIRED
              IF CPYB-ACTION-CODE = 'PY'
                 MOVE 'PGMA001' TO WS-PGM-NAME
              ELSE
                 IF CPYB-ACTION-CODE = 'RF'
                    MOVE 'PGMA001' TO WS-PGM-NAME
                 ELSE
                    EVALUATE TRUE
                       WHEN HIGH-PRIORITY
                          MOVE 'PGMA001' TO WS-PGM-NAME
                       WHEN CPYB-FOREIGN-REQUEST
                          MOVE 'PGMA001' TO WS-PGM-NAME
                       WHEN OTHER
                          MOVE 'PGMA001' TO WS-PGM-NAME
                    END-EVALUATE
                 END-IF
              END-IF

              CALL 'ZCALLPGM' USING WS-PGM-NAME
                                     CPYB-BATCH-CONTEXT

              IF CPYB-PGM-RETURN = '0000'
                 ADD 1 TO WS-PROCESSED-NBR
              ELSE
                 ADD 1 TO WS-ERROR-NBR
              END-IF
           ELSE
              CONTINUE
           END-IF
           .

       3500-EXIT.
           EXIT
           .

       9000-END.
           CLOSE IN-FILE

           DISPLAY 'LINES READ     : ' WS-LINE-NBR
           DISPLAY 'LINES PROCESSED: ' WS-PROCESSED-NBR
           DISPLAY 'LINES ERROR    : ' WS-ERROR-NBR
           .

       9000-EXIT.
           EXIT
           .