       01  CPYB-BATCH-CONTEXT.
           05  CPYB-REQUEST.
               10  CPYB-REQ-ID               PIC X(12).
               10  CPYB-CLIENT-ID            PIC X(10).
               10  CPYB-ACCOUNT-ID           PIC X(12).
               10  CPYB-ACTION-CODE          PIC X(02).
               10  CPYB-CHANNEL              PIC X(03).
               10  CPYB-COUNTRY              PIC X(03).
               10  CPYB-CURRENCY             PIC X(03).
               10  CPYB-AMOUNT               PIC S9(9)V99 COMP-3.
               10  CPYB-FEE                  PIC S9(7)V99 COMP-3.
               10  CPYB-TOTAL                PIC S9(9)V99 COMP-3.
               10  CPYB-STATUS               PIC X(02).
               10  CPYB-PRIORITY             PIC 9(01).
               10  CPYB-RISK-LEVEL           PIC 9(01).
               10  CPYB-SEGMENT              PIC X(02).
               10  CPYB-PRODUCT              PIC X(04).
               10  CPYB-PROCESS-DATE         PIC 9(08).
               10  CPYB-DECISION-CODE        PIC X(02).
               10  CPYB-ERR-CODE             PIC X(04).
               10  CPYB-ERR-MSG              PIC X(60).
               10  CPYB-DB-INFO              PIC X(40).
               10  CPYB-ROUTING-CODE         PIC X(08).
               10  CPYB-PGM-RETURN           PIC X(04).
               10  CPYB-TRACE-ID             PIC X(16).

           05  CPYB-FLAGS.
               10  CPYB-FLG-VALIDATION       PIC X VALUE 'N'.
                   88  CPYB-VALIDATION-OK          VALUE 'Y'.
                   88  CPYB-VALIDATION-KO          VALUE 'N'.
               10  CPYB-FLG-SQL-NEEDED       PIC X VALUE 'N'.
                   88  CPYB-SQL-NEEDED             VALUE 'Y'.
                   88  CPYB-SQL-NOT-NEEDED         VALUE 'N'.
               10  CPYB-FLG-HIGH-AMOUNT      PIC X VALUE 'N'.
                   88  CPYB-HIGH-AMOUNT            VALUE 'Y'.
                   88  CPYB-NOT-HIGH-AMOUNT        VALUE 'N'.
               10  CPYB-FLG-FOREIGN          PIC X VALUE 'N'.
                   88  CPYB-FOREIGN-REQUEST        VALUE 'Y'.
                   88  CPYB-DOMESTIC-REQUEST       VALUE 'N'.
               10  CPYB-FLG-ACCOUNT-FOUND    PIC X VALUE 'N'.
                   88  CPYB-ACCOUNT-FOUND          VALUE 'Y'.
                   88  CPYB-ACCOUNT-NOT-FOUND      VALUE 'N'.
               10  CPYB-FLG-CLIENT-BLOCKED   PIC X VALUE 'N'.
                   88  CPYB-CLIENT-BLOCKED         VALUE 'Y'.
                   88  CPYB-CLIENT-NOT-BLOCKED     VALUE 'N'.
               10  CPYB-FLG-MANUAL-REVIEW    PIC X VALUE 'N'.
                   88  CPYB-MANUAL-REVIEW          VALUE 'Y'.
                   88  CPYB-AUTO-REVIEW            VALUE 'N'.

           05  CPYB-AUDIT.
               10  CPYB-CREATED-BY           PIC X(08).
               10  CPYB-CREATED-TS           PIC X(26).
               10  CPYB-UPDATED-BY           PIC X(08).
               10  CPYB-UPDATED-TS           PIC X(26).