import schedule
import time
import datetime

def recon():
    
    ################################################### INITIATE ####################################################
    # Import Libraries
    import pymysql
    import pandas as pd

    # Setting the Parameters
    host = "3.208.195.34"
    user = "root"
    password = "AlgoTeam123"
    database = "karvy_extraction"

    # Create Database connection
    conn = pymysql.connect(host,user,password,database)

    # Connect with cursor that can enable to write/ edit/ update data on MySQL server
    cursor = conn.cursor()
    # cursor.execute("INSERT INTO `History_Log` SELECT * FROM `Recent_Log`")
    # cursor.execute("Truncate Table `Recent_Log`")
    cursor.execute("DROP TABLE IF EXISTS Temp")
    cursor.execute("UPDATE cms SET `Matched`= 0")
    cursor.execute("UPDATE cms SET `queue`= ''")
    cursor.execute("UPDATE standard_feed SET `ID` = 0")
    cursor.execute("UPDATE standard_feed SET `Matched` = 0")
    cursor.execute("UPDATE standard_feed SET `queue`= ''")
    cursor.execute("UPDATE standard_task SET `Matched_Feed_ID`= ''")
    cursor.execute("UPDATE standard_task SET `Feed_ID`= ''")
    cursor.execute("UPDATE standard_task SET `queue`= ''")
    cursor.execute("UPDATE standard_bank SET `Unmatched_Amount`= `Amount`")
    cursor.execute("UPDATE standard_bank SET `queue`= ''")
    # Commit your changes in the database
    conn.commit()
    
    print('Start')
    print(datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S'))
    
    ################################################### FUNCTIONS ####################################################
    # Notes
    # Group and Sort functions are defined for transformation before Reconciliation
    def group(df,fields,field,Agg):
        gp = df.groupBy(fields).agg({field:Agg})
        return gp.withColumnRenamed(Agg+"("+field+")",field)

    def sort(df,fields):
        return df.orderBy(fields)

    ################################################### CONNECTION ###################################################
    from pyspark import SparkContext, SparkConf, SQLContext
    import pymysql
    import pandas as pd
    from pyspark.sql.functions import col
    import pyspark.sql.functions as fn
    import numpy as np

    appName = "Automation"
    master = "local"
    jar_path = "\\home\\ubuntu\\spark-2.1.1-bin-hadoop2.7\\jars\\mysql-connector-java-8.0.17.jar"
    host = "3.208.195.34"
    port = "3306"
    link_end = "/phpmyadmin"
    user = "root"
    password = "AlgoTeam123"
    database = "karvy_extraction"
    intermediate_table = "Temp"

    # Initiating Spark Session
    conf = SparkConf() \
          .setAppName(appName) \
          .setMaster(master) \
          .set('spark.driver.extraClassPath',jar_path)
    sc = SparkContext(conf=conf)
    sqlContext = SQLContext(sc)
    spark = sqlContext.sparkSession

    # Create Database connection
    conn = pymysql.connect(host,user,password,database)

    ############################################# RECON DEFINITIONS ###################################################
    # Definition and Config DataFrames
    Recon = pd.read_sql("SELECT * FROM Recon", conn)
    Recon_Filter = pd.read_sql("SELECT * FROM Recon_Filter", conn)
    Recon_Group = pd.read_sql("SELECT * FROM Recon_Group", conn)
    Recon_GroupAgg = pd.read_sql("SELECT * FROM Recon_GroupAgg", conn)
    Recon_Sort = pd.read_sql("SELECT * FROM Recon_Sort", conn)

    ####################################################### RECON ###################################################
    #for i in range(len(list(Recon['ID']))):
    for i in range(4):
        #print(i)
        Recon_ID = list(Recon[Recon['ID'] == i+1].Recon_ID)[0]
        Raw_Feed = list(Recon[Recon['ID'] == i+1].Raw_Feed)[0]
        Left_Table = list(Recon[Recon['ID'] == i+1].Left_Table)[0]
        Raw_Join = list(Recon[Recon['ID'] == i+1].Raw_Join)[0]
        Right_Table = list(Recon[Recon['ID'] == i+1].Right_Table)[0]
        Join_Condition = list(Recon[Recon['ID'] == i+1].Join_Condition)[0]
        Column_Selection = list(Recon[Recon['ID'] == i+1].Column_Selection)[0]
        Recon_Update = list(Recon[Recon['ID'] == i+1].Recon_Update)[0]


        if Raw_Feed != '':
    ################################################# Raw Transform #################################################
            # Create Spark DataFrame 
            x = spark.read.format("jdbc") \
                .option("url", "jdbc:mysql://"+host+":"+port+link_end) \
                .option("dbtable", database+'.'+Raw_Feed) \
                .option("user", user) \
                .option("password", password) \
                .option("driver", "com.mysql.jdbc.Driver").load()

            # Raw Filtration
            # Recon Level Filter
            F1 = Recon_Filter[Recon_Filter['Recon_ID']==Recon_ID]
            # Table Level Filter
            F2 = F1[F1['Table']==Raw_Feed]
            # Data Filtration
            if len(F2.index) > 0:
                for i in range(len(F2.index)):
                    x = x.filter(F2.iloc[i]['Condition'])
            else:
                pass

            # Raw Grouping
            # Recon Level Group
            G1 = Recon_Group[Recon_Group['Recon_ID']==Recon_ID]
            # Table Level Group
            G2 = G1[G1['Table']==Raw_Feed]
            # Recon Level GroupAgg
            GA1 = Recon_GroupAgg[Recon_GroupAgg['Recon_ID']==Recon_ID]
            # Table Level GroupAgg
            GA2 = GA1[GA1['Table']==Raw_Feed]
            # Data Grouping
            if len(G2.index) > 0:
                x = group(x,list(G2['Column']),GA2['Column'].iloc[0],GA2['Agg'].iloc[0])
            else:
                pass

            # Raw Sorting
            # Recon Level Sort
            S1 = Recon_Sort[Recon_Sort['Recon_ID']==Recon_ID]
            # Table Level Sort
            S2 = S1[S1['Table']==Raw_Feed].sort_values('Order')
            # Filtering only Highly Ranked Columns for Sorting
            if Recon_ID == 'FeedvsTask2':
                S2 = S2[S2['Rank']>=100]
            else:
                pass
            # Data Sorting
            if len(S2.index) > 0:
                x = sort(x,list(S2['Column']))
            else:
                pass

            # Raw View
            x.createOrReplaceTempView(Raw_Feed)
        else:
            pass


    ################################################# Left Transform #################################################
        # Create Spark DataFrame 
        x = spark.read.format("jdbc") \
            .option("url", "jdbc:mysql://"+host+":"+port+link_end) \
            .option("dbtable", database+'.'+Left_Table) \
            .option("user", user) \
            .option("password", password) \
            .option("driver", "com.mysql.jdbc.Driver").load()

        # Left Filtration
        # Recon Level Filter
        F1 = Recon_Filter[Recon_Filter['Recon_ID']==Recon_ID]
        # Table Level Filter
        F2 = F1[F1['Table']==Left_Table]
        # Data Filtration
        if len(F2.index) > 0:
            for i in range(len(F2.index)):
                x = x.filter(F2.iloc[i]['Condition'])
        else:
            pass

        # Left Grouping
        # Recon Level Group
        G1 = Recon_Group[Recon_Group['Recon_ID']==Recon_ID]
        # Table Level Group
        G2 = G1[G1['Table']==Left_Table]
        # Recon Level GroupAgg
        GA1 = Recon_GroupAgg[Recon_GroupAgg['Recon_ID']==Recon_ID]
        # Table Level GroupAgg
        GA2 = GA1[GA1['Table']==Left_Table]
        # Data Grouping
        if len(G2.index) > 0:
            x = group(x,list(G2['Column']),GA2['Column'].iloc[0],GA2['Agg'].iloc[0])
        else:
            pass

        # Left Sorting
        # Recon Level Sort
        S1 = Recon_Sort[Recon_Sort['Recon_ID']==Recon_ID]
        # Table Level Sort
        S2 = S1[S1['Table']==Left_Table].sort_values('Order')
        # Data Sorting
        if len(S2.index) > 0:
            x = sort(x,list(S2['Column']))
        else:
            pass

        # Left View
        x.createOrReplaceTempView(Left_Table)


        if Raw_Feed != '':
    ###################################################### Raw & Left Join ############################################
            # Join the two SQL views based on Join Condition
            raw = spark.sql(Raw_Join)
            raw.createOrReplaceTempView(Left_Table)
        else:
            pass


    ################################################# Right Transform #################################################
        # Create Spark DataFrame 
        x = spark.read.format("jdbc") \
            .option("url", "jdbc:mysql://"+host+":"+port+link_end) \
            .option("dbtable", database+'.'+Right_Table) \
            .option("user", user) \
            .option("password", password) \
            .option("driver", "com.mysql.jdbc.Driver").load()

        # Right Filtration
        # Recon Level Filter
        F1 = Recon_Filter[Recon_Filter['Recon_ID']==Recon_ID]
        # Table Level Filter
        F2 = F1[F1['Table']==Right_Table]
        # Data Filtration
        if len(F2.index) > 0:
            for i in range(len(F2.index)):
                x = x.filter(F2.iloc[i]['Condition'])
        else:
            pass

        # Right Grouping
        # Recon Level Group
        G1 = Recon_Group[Recon_Group['Recon_ID']==Recon_ID]
        # Table Level Group
        G2 = G1[G1['Table']==Right_Table]
        # Recon Level GroupAgg
        GA1 = Recon_GroupAgg[Recon_GroupAgg['Recon_ID']==Recon_ID]
        # Table Level GroupAgg
        GA2 = GA1[GA1['Table']==Right_Table]
        # Data Grouping
        if len(G2.index) > 0:
            x = group(x,list(G2['Column']),GA2['Column'].iloc[0],GA2['Agg'].iloc[0])
        else:
            pass

        # Right Sorting
        # Recon Level Sort
        S1 = Recon_Sort[Recon_Sort['Recon_ID']==Recon_ID]
        # Table Level Sort
        S2 = S1[S1['Table']==Right_Table]
        S2 = S2[S2['Left_Table']==Raw_Feed].sort_values('Order')
        # Filtering only Highly Ranked Columns for Sorting
        if Recon_ID == 'FeedvsTask2':
            S2 = S2[S2['Rank']>=100]
        else:
            pass
        # Data Sorting
        if len(S2.index) > 0:
            x = sort(x,list(S2['Column']))
        else:
            pass

        # Right View
        x.createOrReplaceTempView(Right_Table)


    ###################################################### Recon #################################################
        # Join the two SQL views based on Join Condition
        recon = spark.sql(Join_Condition)
        recon = recon.select(Column_Selection.split(","))
        cursor = conn.cursor()
        if recon.count() != 0:
            recon.write \
                .format("jdbc") \
                .option("url", "jdbc:mysql://"+host+":"+port+link_end) \
                .option("dbtable", database+'.'+intermediate_table) \
                .option("user", user) \
                .option("password", password) \
                .save()


            # Update Database
            for i in range(len(Recon_Update.split(";"))):
                cursor.execute(Recon_Update.split(";")[i])
            conn.commit()
        else:
            pass


    # Close the cursor
    cursor.close()
    # Close the connection
    conn.close()
    # Close SparkSession
    spark.stop()
            
    print('Done')
    print(datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S'))
            
schedule.every().day.at("11:01").do(recon)
schedule.every(8).minutes.do(recon)

if __name__ == '__main__':
    while True: 
        schedule.run_pending() 
        time.sleep(60)