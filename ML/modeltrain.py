import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.tree import DecisionTreeClassifier, plot_tree
from sklearn.ensemble import RandomForestClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.metrics import accuracy_score, confusion_matrix, classification_report
from sklearn.cluster import KMeans
from wordcloud import WordCloud

# -------------------------------
# 1. Load dataset
# -------------------------------
file_path = "social_media_engagement_data.xlsx"
df = pd.read_excel(file_path)

# -------------------------------
# 2. Preprocessing & EDA
# -------------------------------

# Handle missing values
df['Likes'] = df['Likes'].fillna(0)
df['Comments'] = df['Comments'].fillna(0)
df['Shares'] = df['Shares'].fillna(0)
df['Reach'] = df['Reach'].fillna(df['Reach'].median())
df['Engagement Rate'] = df['Engagement Rate'].fillna(df['Engagement Rate'].median())
df['Sentiment'] = df['Sentiment'].fillna('Neutral')

# Encode categorical variables
le_platform = LabelEncoder()
df['Platform_enc'] = le_platform.fit_transform(df['Platform'])

le_posttype = LabelEncoder()
df['PostType_enc'] = le_posttype.fit_transform(df['Post Type'])

le_gender = LabelEncoder()
df['Gender_enc'] = le_gender.fit_transform(df['Audience Gender'])

# Create Engagement Score & Level
df['EngagementScore'] = df['Likes'] + 2*df['Comments'] + 3*df['Shares']
df['EngagementLevel'] = pd.cut(df['EngagementScore'], bins=[-1,50,200,10000], labels=['Low','Medium','High'])

# -------------------------------
# 3. Visualizations for EDA
# -------------------------------
def perform_eda():
    print("\n--- EDA & Visualizations ---\n")
    
    # Shape & info
    print("Dataset Shape:", df.shape)
    print("\nDataset Info:")
    print(df.info())
    
    # Summary statistics
    print("\nSummary statistics:")
    print(df.describe())
    
    # Histograms
    numeric_cols = ['Likes','Comments','Shares','Reach','Engagement Rate']
    df[numeric_cols].hist(figsize=(10,6))
    plt.suptitle("Histograms of Numeric Features")
    plt.show()
    
    # Boxplot & Violin plot for EngagementScore
    plt.figure(figsize=(8,4))
    sns.boxplot(x='EngagementScore', data=df)
    plt.title("Boxplot of Engagement Score")
    plt.show()
    
    plt.figure(figsize=(8,4))
    sns.violinplot(x='EngagementScore', data=df)
    plt.title("Violin Plot of Engagement Score")
    plt.show()
    
    # Heatmap
    plt.figure(figsize=(8,6))
    sns.heatmap(df[numeric_cols].corr(), annot=True, cmap='coolwarm')
    plt.title("Heatmap of Numeric Features")
    plt.show()




# -------------------------------
# 4. KNN - Sentiment Prediction
# -------------------------------
def knn_sentiment():
    print("\nRunning KNN - Sentiment Prediction...\n")
    features = ['Likes','Comments','Shares','Reach','Engagement Rate']
    X = df[features]
    y = df['Sentiment']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    knn = KNeighborsClassifier(n_neighbors=5)
    knn.fit(X_train_scaled, y_train)
    y_pred = knn.predict(X_test_scaled)
    
    print("Accuracy:", round(accuracy_score(y_test, y_pred),4))
    cm = confusion_matrix(y_test, y_pred)
    print("\nConfusion Matrix:\n", cm)
    
    # Display confusion matrix as heatmap
    plt.figure(figsize=(6,4))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=knn.classes_, yticklabels=knn.classes_)
    plt.xlabel('Predicted')
    plt.ylabel('Actual')
    plt.title("Confusion Matrix - KNN Sentiment Prediction")
    plt.show()





# -------------------------------
# 5. Decision Tree & Random Forest - Engagement Level
# -------------------------------
def tree_engagement():
    print("\nRunning Decision Tree & Random Forest - Engagement Level Prediction...\n")
    features = ['Likes','Comments','Shares','Reach','Engagement Rate','Platform_enc','PostType_enc','Gender_enc']
    X = df[features]
    y = df['EngagementLevel']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Decision Tree
    dt = DecisionTreeClassifier(max_depth=5, random_state=42)
    dt.fit(X_train, y_train)
    y_pred_dt = dt.predict(X_test)
    print("Decision Tree Accuracy:", round(accuracy_score(y_test, y_pred_dt),4))
    
    # Plot Decision Tree with larger text
    plt.figure(figsize=(15, 5))
    plot_tree(
        dt,
        feature_names=features,
        class_names=['Low', 'Medium', 'High'],
        filled=True,
        rounded=True,
        fontsize=5  # increase this if you want bigger text (try 14 or 16)
    )
    plt.title("Decision Tree - Engagement Level", fontsize=18)
    plt.show()
    
    # Random Forest
    rf = RandomForestClassifier(n_estimators=100, max_depth=7, random_state=42)
    rf.fit(X_train, y_train)
    y_pred_rf = rf.predict(X_test)
    print("Random Forest Accuracy:", round(accuracy_score(y_test, y_pred_rf),4))
    
    # Feature importance
    feat_importances = pd.Series(rf.feature_importances_, index=features)
    feat_importances.sort_values().plot(kind='barh', figsize=(10, 6))
    plt.title("Random Forest Feature Importance", fontsize=14)
    plt.xlabel("Importance Score", fontsize=12)
    plt.ylabel("Features", fontsize=12)
    plt.show()








# -------------------------------
# 6. Naive Bayes - Post Type Classification
# -------------------------------
def naive_posttype():
    print("\nRunning Naive Bayes - Post Type Classification...\n")
    features = ['Likes','Comments','Shares','Reach','Engagement Rate']
    X = df[features]
    y = df['Post Type']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    nb = GaussianNB()
    nb.fit(X_train_scaled, y_train)
    y_pred = nb.predict(X_test_scaled)
    
    print("Accuracy:", round(accuracy_score(y_test, y_pred),4))
    cm = confusion_matrix(y_test, y_pred)
    print("\nConfusion Matrix:\n", cm)
    
    # Heatmap of confusion matrix
    plt.figure(figsize=(6,4))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Oranges', xticklabels=nb.classes_, yticklabels=nb.classes_)
    plt.xlabel('Predicted')
    plt.ylabel('Actual')
    plt.title("Confusion Matrix - Naive Bayes Post Type Classification")
    plt.show()





    

# -------------------------------
# 7. K-Means Clustering - Posts by Engagement
# -------------------------------
def kmeans_cluster():
    print("\nRunning K-Means Clustering on Engagement Metrics...\n")
    features = ['Likes','Comments','Shares','Reach','Engagement Rate']
    X = df[features]
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    kmeans = KMeans(n_clusters=3, random_state=42)
    df['Cluster'] = kmeans.fit_predict(X_scaled)
    
    sns.scatterplot(x='Likes', y='Shares', hue='Cluster', data=df, palette='Set1')
    plt.title("K-Means Clustering of Posts by Engagement")
    plt.show()

# -------------------------------
# 8. Word Cloud - Post Content
# -------------------------------
def word_cloud():
    print("\nGenerating Word Cloud for Post Captions...\n")
    text = " ".join(df['Post Content'].dropna().astype(str))
    wordcloud = WordCloud(width=800, height=400, background_color='white').generate(text)
    plt.figure(figsize=(15,7))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis('off')
    plt.title("Word Cloud of Post Captions")
    plt.show()

# -------------------------------
# 9. Menu
# -------------------------------
def menu():
    perform_eda()
    while True:
        print("\nSelect an option:")
        print("1. Sentiment Analysis Prediction (KNN)")
        print("2. Engagement Level Prediction (Decision Tree & Random Forest)")
        print("3. Post Type Classification (Naive Bayes)")
        print("4. Clustering (K-Means)")
        print("5. Visualizations (Word Cloud)")
        print("6. Exit")
        choice = input("Enter your choice (1-6): ")
        
        if choice=='1':
            knn_sentiment()
        elif choice=='2':
            tree_engagement()
        elif choice=='3':
            naive_posttype()
        elif choice=='4':
            kmeans_cluster()
        elif choice=='5':
            word_cloud()
        elif choice=='6':
            print("Exiting...")
            break
        else:
            print("Invalid choice. Try again.")

if __name__=="__main__":
    menu()
