﻿
# Add these imports at the top of the file
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
import tensorflow as tf
import pickle
import joblib
from PIL import Image
from io import BytesIO
import base64
import nltk
import re
import warnings
warnings.filterwarnings('ignore')

# Add these functions after the existing imports and before the page config

def train_expense_predictor(transaction_data):
    """Train a model to predict monthly expenses based on historical data"""
    # Prepare data
    df = transaction_data.copy()
    df['date'] = pd.to_datetime(df['date'])
    df['month'] = df['date'].dt.month
    df['day_of_week'] = df['date'].dt.dayofweek

    # Only use expense records
    expenses = df[df['type'] == 'expense'].copy()

    # Feature engineering
    features = pd.get_dummies(expenses[['category', 'month', 'day_of_week']])
    target = expenses['amount'].abs()  # Use absolute value since expenses are negative

    # Train model
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(features, target)

    return model, features.columns

def predict_next_month_expenses(model, feature_names, transaction_data):
    """Predict next month's expenses based on the trained model"""
    # Prepare prediction data for next month
    next_month = (datetime.now().month % 12) + 1

    # Get unique categories
    categories = transaction_data['category'].unique()
    categories = [c for c in categories if c != 'Income']

    predictions = {}
    for category in categories:
        # Create an empty dataframe with expected features
        pred_df = pd.DataFrame(columns=feature_names)
        pred_df.loc[0] = 0  # Fill with zeros initially

        # Set category and month
        for col in feature_names:
            if col == f"category_{category}":
                pred_df[col] = 1
            if col == f"month_{next_month}":
                pred_df[col] = 1

        # Predict
        amount = model.predict(pred_df)[0]
        predictions[category] = amount

    return predictions

def cluster_transactions(transaction_data):
    """Cluster transactions to identify spending patterns"""
    # Prepare data
    df = transaction_data.copy()

    # Filter to expenses only
    expenses = df[df['type'] == 'expense'].copy()

    # Feature engineering
    expenses['date'] = pd.to_datetime(expenses['date'])
    expenses['day_of_month'] = expenses['date'].dt.day
    expenses['day_of_week'] = expenses['date'].dt.dayofweek
    expenses['amount_abs'] = expenses['amount'].abs()

    # Encode categories
    cat_encoded = pd.get_dummies(expenses['category'])

    # Combine features
    features = pd.concat([
        expenses[['amount_abs', 'day_of_month', 'day_of_week']].reset_index(drop=True),
        cat_encoded.reset_index(drop=True)
    ], axis=1)

    # Scale features
    scaler = StandardScaler()
    features_scaled = scaler.fit_transform(features)

    # Apply PCA for dimension reduction
    pca = PCA(n_components=min(5, features.shape[1]))
    features_pca = pca.fit_transform(features_scaled)

    # Apply K-means clustering
    kmeans = KMeans(n_clusters=3, random_state=42)
    clusters = kmeans.fit_predict(features_pca)

    # Add cluster information to original data
    expenses['cluster'] = clusters

    return expenses, kmeans, scaler, pca

def generate_spending_insights(clustered_data):
    """Generate insights based on clustered transactions"""
    insights = []

    # Analyze spending by cluster
    cluster_stats = clustered_data.groupby('cluster').agg({
        'amount_abs': ['mean', 'sum', 'count'],
        'category': lambda x: x.value_counts().index[0],
        'day_of_week': 'mean'
    })

    # Generate insights
    for cluster in cluster_stats.index:
        count = cluster_stats.loc[cluster, ('amount_abs', 'count')]
        total = cluster_stats.loc[cluster, ('amount_abs', 'sum')]
        avg = cluster_stats.loc[cluster, ('amount_abs', 'mean')]
        top_category = cluster_stats.loc[cluster, ('category', '<lambda>')]

        # Frequent small expenses
        if count > 10 and avg < 20:
            insights.append(f"You have {count:.0f} frequent small expenses averaging €{avg:.2f}, mostly on {top_category}. These add up to €{total:.2f}.")

        # Large occasional expenses
        if count < 5 and avg > 100:
            insights.append(f"You have {count:.0f} large expenses on {top_category} averaging €{avg:.2f}. Consider budgeting €{total/3:.2f} monthly for these expenses.")

    # Add general insights
    cat_spending = clustered_data.groupby('category')['amount_abs'].sum().sort_values(ascending=False)
    top_category = cat_spending.index[0]
    top_amount = cat_spending.iloc[0]

    insights.append(f"Your highest spending category is {top_category} at €{top_amount:.2f}. This represents {(top_amount/cat_spending.sum()*100):.1f}% of your expenses.")

    return insights

def build_budget_optimizer(transaction_data, target_savings):
    """Build a model to optimize budget allocation"""
    # Prepare data
    df = transaction_data.copy()
    expenses = df[df['type'] == 'expense'].copy()

    # Get total expenses by category
    category_totals = expenses.groupby('category')['amount'].sum().abs()

    # Calculate current total expenses
    total_expenses = category_totals.sum()

    # Calculate needed reduction to meet target savings
    income = df[df['type'] == 'income']['amount'].sum()
    current_savings = income - total_expenses
    savings_gap = target_savings - current_savings

    # If already saving enough
    if savings_gap <= 0:
        return None, None, current_savings

    # Calculate % reduction needed in each category
    # Exclude essentials with higher weights (lower reduction %)
    category_weights = {
        'Groceries': 0.3,
        'Utilities': 0.3,
        'Transport': 0.5,
        'Dining': 0.8,
        'Entertainment': 1.0,
        'Shopping': 0.9
    }

    # Fill missing weights
    for cat in category_totals.index:
        if cat not in category_weights:
            category_weights[cat] = 0.7

    # Calculate suggested reductions
    suggested_budget = {}
    for category, amount in category_totals.items():
        weight = category_weights.get(category, 0.7)
        reduction = min(amount * 0.3 * weight, savings_gap * (amount / total_expenses))
        suggested_budget[category] = amount - reduction

    # Calculate new savings with this budget
    new_savings = income - sum(suggested_budget.values())

    return suggested_budget, category_weights, new_savings

def predict_investment_returns(current_amount, monthly_contribution, years, risk_level):
    """Predict investment returns based on risk level"""
    # Define expected returns and volatility by risk level
    risk_profiles = {
        'low': {'return': 0.05, 'volatility': 0.05},
        'medium': {'return': 0.08, 'volatility': 0.12},
        'high': {'return': 0.11, 'volatility': 0.20}
    }

    profile = risk_profiles.get(risk_level, risk_profiles['medium'])

    # Run Monte Carlo simulation
    simulations = 100
    periods = years * 12

    results = np.zeros((simulations, periods+1))
    results[:, 0] = current_amount

    for sim in range(simulations):
        for period in range(1, periods+1):
            # Monthly return with randomness
            monthly_return = np.random.normal(
                profile['return']/12,
                profile['volatility']/np.sqrt(12)
            )

            # Apply return to previous balance
            results[sim, period] = results[sim, period-1] * (1 + monthly_return) + monthly_contribution

    # Calculate percentiles
    percentiles = [10, 50, 90]
    percentile_values = np.percentile(results[:, -1], percentiles)

    # Get the trajectory of the median path
    median_sim_idx = np.argmin(np.abs(results[:, -1] - percentile_values[1]))
    median_path = results[median_sim_idx, :]

    return {
        'percentiles': dict(zip(percentiles, percentile_values)),
        'median_path': median_path,
        'periods': np.arange(periods+1),
        'expected_value': percentile_values[1]
    }

def build_subscription_recommendation_model():
    """Build a model to recommend subscription level based on user patterns"""
    # This would normally use real training data
    # For demonstration, we'll create a simple decision tree

    # Features would be:
    # - Monthly income
    # - Number of financial goals
    # - Transaction volume
    # - Savings amount
    # - Investment amount

    # Create a simple decision function
    def recommend_subscription(income, goals, transaction_volume, savings, investments):
        score = 0

        # Income factor
        if income < 2000:
            score += 0
        elif income < 4000:
            score += 1
        else:
            score += 2

        # Goals factor
        if goals <= 2:
            score += 0
        elif goals <= 5:
            score += 1
        else:
            score += 2

        # Transaction volume
        if transaction_volume < 20:
            score += 0
        elif transaction_volume < 50:
            score += 1
        else:
            score += 2

        # Savings/Investment factor
        combined = savings + investments
        if combined < 1000:
            score += 0
        elif combined < 5000:
            score += 1
        else:
            score += 2

        # Map score to subscription
        if score <= 3:
            return "Basic"
        elif score <= 6:
            return "Pro"
        else:
            return "Elite"

    return recommend_subscription

def analyze_sentiment(text):
    """Analyze sentiment in text using a simple lexicon-based approach"""
    # Simple sentiment lexicon
    positive_words = ['great', 'good', 'positive', 'excellent', 'profit', 'gain', 'increase', 'up', 'higher', 'growth']
    negative_words = ['bad', 'poor', 'negative', 'loss', 'decrease', 'down', 'lower', 'decline', 'debt', 'worry']

    # Tokenize
    words = re.findall(r'\w+', text.lower())

    # Count sentiment words
    positive_count = sum(1 for word in words if word in positive_words)
    negative_count = sum(1 for word in words if word in negative_words)

    # Calculate sentiment score (-1 to 1)
    total_count = positive_count + negative_count
    if total_count > 0:
        sentiment_score = (positive_count - negative_count) / total_count
    else:
        sentiment_score = 0

    # Classify sentiment
    if sentiment_score > 0.2:
        sentiment = "positive"
    elif sentiment_score < -0.2:
        sentiment = "negative"
    else:
        sentiment = "neutral"

    return {
        'score': sentiment_score,
        'classification': sentiment,
        'positive_words': positive_count,
        'negative_words': negative_count
    }

def create_financial_health_score(transaction_data, goals, balance, savings, investments):
    """Create a comprehensive financial health score"""
    # Calculate income and expenses
    total_income = transaction_data[transaction_data['type'] == 'income']['amount'].sum()
    total_expenses = transaction_data[transaction_data['type'] == 'expense']['amount'].sum().abs()

    # Calculate metrics
    if total_income > 0:
        savings_rate = (total_income - total_expenses) / total_income * 100
    else:
        savings_rate = 0

    # Emergency fund ratio (months of expenses covered)
    monthly_expenses = total_expenses / 3  # Assuming 3 months of data
    if monthly_expenses > 0:
        emergency_fund_ratio = savings / monthly_expenses
    else:
        emergency_fund_ratio = 0

    # Goal progress
    goal_progress = []
    for goal in goals:
        progress = (goal['current'] / goal['target']) * 100
        goal_progress.append(progress)
    avg_goal_progress = sum(goal_progress) / len(goal_progress) if goal_progress else 0

    # Investment ratio (investments to total assets)
    total_assets = balance + savings + investments
    if total_assets > 0:
        investment_ratio = investments / total_assets * 100
    else:
        investment_ratio = 0

    # Calculate scores for each component (0-100)
    scores = {
        'Savings Rate': min(100, savings_rate * 2),  # 50% savings rate -> 100 score
        'Emergency Fund': min(100, emergency_fund_ratio * 33.3),  # 3 months -> 100 score
        'Goal Progress': min(100, avg_goal_progress * 1.5),  # 67% progress -> 100 score
        'Investment Strategy': min(100, investment_ratio * 2),  # 50% in investments -> 100 score
        'Debt Management': 90  # Placeholder without real debt data
    }

    # Overall score is weighted average
    weights = {
        'Savings Rate': 0.25,
        'Emergency Fund': 0.25,
        'Goal Progress': 0.2,
        'Investment Strategy': 0.15,
        'Debt Management': 0.15
    }

    overall_score = sum(scores[k] * weights[k] for k in scores)

    return {
        'overall': round(overall_score),
        'components': scores
    }

def generate_custom_insights(transaction_data, financial_health):
    """Generate personalized insights based on transaction data and financial health"""
    insights = []

    # Analyze spending patterns
    df = transaction_data.copy()
    expenses = df[df['type'] == 'expense'].copy()

    # Convert date to datetime
    expenses['date'] = pd.to_datetime(expenses['date'])
    expenses['month'] = expenses['date'].dt.month
    expenses['week'] = expenses['date'].dt.isocalendar().week
    expenses['amount_abs'] = expenses['amount'].abs()

    # Get monthly spending
    current_month = datetime.now().month
    prev_month = current_month - 1 if current_month > 1 else 12

    current_month_data = expenses[expenses['month'] == current_month]
    prev_month_data = expenses[expenses['month'] == prev_month]

    # Category comparisons
    if not current_month_data.empty and not prev_month_data.empty:
        for category in expenses['category'].unique():
            curr_cat = current_month_data[current_month_data['category'] == category]['amount_abs'].sum()
            prev_cat = prev_month_data[prev_month_data['category'] == category]['amount_abs'].sum()

            if prev_cat > 0:
                change_pct = (curr_cat - prev_cat) / prev_cat * 100

                if change_pct > 20:
                    insights.append(f"Your spending on {category} has increased by {change_pct:.1f}% this month.")
                elif change_pct < -20:
                    insights.append(f"Great job! You've reduced your {category} spending by {-change_pct:.1f}% this month.")

    # Savings insights
    savings_rate_score = financial_health['components']['Savings Rate']
    if savings_rate_score < 50:
        insights.append("Your savings rate is below the recommended level. Consider the 50/30/20 rule: 50% for needs, 30% for wants, and 20% for savings.")
    elif savings_rate_score > 80:
        insights.append("You have an excellent savings rate! Consider putting some of your savings into investments for better long-term growth.")

    # Emergency fund insights
    emergency_score = financial_health['components']['Emergency Fund']
    if emergency_score < 60:
        insights.append("Your emergency fund could use a boost. Aim for 3-6 months of expenses saved in an accessible account.")

    # Investment insights
    investment_score = financial_health['components']['Investment Strategy']
    if investment_score < 40:
        insights.append("Consider increasing your investments to build long-term wealth. Even small regular contributions can grow significantly over time.")

    # Goal insights
    goal_score = financial_health['components']['Goal Progress']
    if goal_score < 50:
        insights.append("You're falling behind on your financial goals. Consider revisiting your timeline or increasing your contributions.")

    # Limit insights to top 5
    if len(insights) > 5:
        insights = insights[:5]

    return insights

# Add a new function to initialize ML models
def initialize_ml_models():
    """Initialize all ML models needed for the app"""
    # For the purpose of this demo, we're generating random transaction data
    # In a real app, you'd load this from a database
    if 'transactions' not in st.session_state:
        # Generate some sample transactions
        categories = ["Groceries", "Dining", "Entertainment", "Transport", "Shopping", "Utilities", "Income"]
        amounts = [random.uniform(5, 200) for _ in range(30)]
        dates = [(datetime.now() - timedelta(days=random.randint(0, 30))).strftime("%Y-%m-%d") for _ in range(30)]

        st.session_state.transactions = pd.DataFrame({
            "date": dates,
            "category": [random.choice(categories) for _ in range(30)],
            "amount": amounts,
            "description": [f"Transaction {i+1}" for i in range(30)]
        })
        st.session_state.transactions["type"] = ["expense" if cat != "Income" else "income" for cat in st.session_state.transactions["category"]]
        st.session_state.transactions["amount"] = [
            -amt if cat != "Income" else amt
            for amt, cat in zip(st.session_state.transactions["amount"], st.session_state.transactions["category"])
        ]

    # Train models when app starts
    if 'ml_models' not in st.session_state:
        # Expense predictor
        expense_model, feature_names = train_expense_predictor(st.session_state.transactions)

        # Clustering model for spending patterns
        clustered_transactions, kmeans_model, scaler, pca = cluster_transactions(st.session_state.transactions)

        # Budget optimizer
        target_monthly_savings = 300  # Example target
        budget_model, category_weights, projected_savings = build_budget_optimizer(
            st.session_state.transactions, target_monthly_savings
        )

        # Subscription recommendation model
        subscription_model = build_subscription_recommendation_model()

        # Financial health score
        financial_health = create_financial_health_score(
            st.session_state.transactions,
            st.session_state.goals,
            st.session_state.balance,
            st.session_state.savings,
            st.session_state.investments
        )

        # Store all models and data
        st.session_state.ml_models = {
            'expense_predictor': {
                'model': expense_model,
                'feature_names': feature_names
            },
            'spending_clusters': {
                'data': clustered_transactions,
                'kmeans': kmeans_model,
                'scaler': scaler,
                'pca': pca
            },
            'budget_optimizer': {
                'suggested_budget': budget_model,
                'weights': category_weights,
                'projected_savings': projected_savings
            },
            'subscription_recommender': subscription_model,
            'financial_health': financial_health
        }

        # Generate insights
        cluster_insights = generate_spending_insights(clustered_transactions)
        custom_insights = generate_custom_insights(st.session_state.transactions, financial_health)

        # Combine insights and store
        st.session_state.insights = custom_insights + cluster_insights
        if len(st.session_state.insights) > 5:
            st.session_state.insights = st.session_state.insights[:5]

# Now modify the display_dashboard function to incorporate ML insights
def display_dashboard():
    st.markdown("<h2>Dashboard</h2>", unsafe_allow_html=True)

    # Ensure ML models are initialized
    if 'ml_models' not in st.session_state:
        initialize_ml_models()

    # Top cards section
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(f"""
        <div class="highlight-card">
            <h4 style="margin-top: 0;">Total Balance</h4>
            <h2 style="margin: 0;">€{st.session_state.balance:.2f}</h2>
            <p>Available funds</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="secondary-card">
            <h4 style="margin-top: 0;">Savings</h4>
            <h2 style="margin: 0;">€{st.session_state.savings:.2f}</h2>
            <p>Growing at 3.5% APY</p>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="secondary-card">
            <h4 style="margin-top: 0;">Investments</h4>
            <h2 style="margin: 0;">€{st.session_state.investments:.2f}</h2>
            <p>+5.2% this month</p>
        </div>
        """, unsafe_allow_html=True)

    # AI Financial Summary
    st.markdown("<h3>AI Financial Summary</h3>", unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1])

    with col1:
        # Financial Health Score from ML model
        financial_health = st.session_state.ml_models['financial_health']
        overall_score = financial_health['overall']

        # Create color based on score
        if overall_score >= 80:
            score_color = "#00D37F"  # Green
        elif overall_score >= 60:
            score_color = "#FFD700"  # Yellow/Gold
        else:
            score_color = "#FF6B6B"  # Red

        st.markdown(f"""
        <div style="padding: 1rem; background-color: #f8f9fa; border-radius: 10px;">
            <div style="display: flex; align-items: center; justify-content: space-between;">
                <div>
                    <h4 style="margin: 0;">AI Financial Health Score</h4>
                    <p style="margin-top: 0.5rem;">Based on your spending patterns, savings, and goals</p>
                </div>
                <div style="width: 80px; height: 80px; border-radius: 50%; background-color: {score_color}; display: flex; align-items: center; justify-content: center;">
                    <span style="color: white; font-size: 24px; font-weight: 600;">{overall_score}</span>
                </div>
            </div>
            <div class="progress-container" style="margin-top: 1rem;">
                <div class="progress-bar" style="width: {overall_score}%; background-color: {score_color}"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        # AI-predicted cash flow
        if 'expense_predictor' in st.session_state.ml_models:
            expense_model = st.session_state.ml_models['expense_predictor']['model']
            feature_names = st.session_state.ml_models['expense_predictor']['feature_names']

            predictions = predict_next_month_expenses(expense_model, feature_names, st.session_state.transactions)
            total_predicted = sum(predictions.values())

            # Calculate predicted savings
            monthly_income = st.session_state.transactions[st.session_state.transactions['type'] == 'income']['amount'].sum() / 3
            predicted_savings = monthly_income - total_predicted

            st.markdown(f"""
            <div style="padding: 1rem; background-color: #f8f9fa; border-radius: 10px; height: 100%;">
                <h4 style="margin-top: 0;">AI Prediction</h4>
                <p style="margin: 0;">Next month's expenses: <strong>€{total_predicted:.2f}</strong></p>
                <p style="margin: 0;">Predicted savings: <strong style="color: {ACCENT_COLOR};">€{predicted_savings:.2f}</strong></p>
                <p style="margin-top: 0.5rem; font-size: 0.8rem;">Based on your spending patterns</p>
            </div>
            """, unsafe_allow_html=True)

    # Round-up savings feature
    st.markdown("<h3>Round-up Savings</h3>", unsafe_allow_html=True)
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown(f"""
        <div style="padding: 1rem; background-color: #f8f9fa; border-radius: 10px;">
            <h4 style="margin-top: 0;">Round-up Savings</h4>
            <p>We round up your transactions and save the difference.</p>
            <div class="progress-container">
                <div class="progress-bar" style="width: 65%; background-color: {PRIMARY_COLOR}"></div>
            </div>
            <p>€{st.session_state.roundups:.2f} saved this month through round-ups</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("<div style='height: 100%; display: flex; align-items: center; justify-content: center;'>", unsafe_allow_html=True)
        if st.button("Boost Round-up"):
            st.session_state.roundups += 5.0
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # Recent transactions and spending analysis
    col1, col2 = st.columns([3, 2])

    with col1:
        st.markdown("<h3>Recent Transactions</h3>", unsafe_allow_html=True)
        recent_transactions = st.session_state.transactions.sort_values(by="date", ascending=False).head(5)

        for _, tx in recent_transactions.iterrows():
            sign = "+" if tx["amount"] > 0 else "-"
            color = ACCENT_COLOR if tx["amount"] > 0 else TEXT_COLOR

            st.markdown(f"""
            <div style="padding: 0.75rem; border-bottom: 1px solid #e0e0e0; display: flex; justify-content: space-between;">
                <div>
                    <p style="margin: 0; font-weight: 500;">{tx["description"]}</p>
                    <p style="margin: 0; color: gray; font-size: 0.8rem;">{tx["date"]} • {tx["category"]}</p>
                </div>
                <div>
                    <p style="margin: 0; font-weight: 500; color: {color};">{sign}€{abs(tx["amount"]):.2f}</p>
                </div>
            </div>
            """, unsafe_allow_html=True)

        if st.button("See All Transactions"):
            navigate_to("transactions")
            st.rerun()

    with col2:
        st.markdown("<h3>AI Spending Analysis</h3>", unsafe_allow_html=True)

        # Use the clustering model to visualize spending patterns
        if 'spending_clusters' in st.session_state.ml_models:
            clustered_data = st.session_state.ml_models['spending_clusters']['data']

            # Prepare data for the chart
            expense_data = st.session_state.transactions[st.session_state.transactions["type"] == "expense"]
            category_spending = expense_data.groupby("category")["amount"].sum().abs().reset_index()

            fig = px.pie(
                category_spending,
                values="amount",
                names="category",
                hole=0.4,
                color_discrete_sequence=px.colors.sequential.Purples_r
            )
            fig.update_layout(margin=dict(t=0, b=0, l=20, r=20), height=300)
            st.plotly_chart(fig, use_container_width=True)

    # AI Insights
    st.markdown("<h3>AI Financial Insights</h3>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    for i, (col, insight) in enumerate(zip([col1, col2, col3], st.session_state.insights)):
        if i < len(st.session_state.insights):
            with col:
                st.markdown(f"""
                <div style="padding: 1rem; background-color: #f8f9fa; border-radius: 10px; height: 100%;">
                    <p style="margin: 0;">{insight}</p>
                </div>
                """, unsafe_allow_html=True)

    # Financial Goals with AI-powered progress prediction
    st.markdown("<h3>Financial Goals</h3>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    for i, goal in enumerate(st.session_state.goals):
        progress = (goal["current"] / goal["target"]) * 100

        # AI prediction for goal completion
        monthly_contribution = goal["current"] / 3  # Rough estimate
        months_to_complete = (goal["target"] - goal["current"]) / monthly_contribution if monthly_contribution > 0 else float('inf')

        if months_to_complete != float('inf'):
            estimated_completion = datetime.now() + timedelta(days=30 * months_to_complete)
            completion_date = estimated_completion.strftime("%Y-%m-%d")
            target_date = goal.get("target_date", "Not set")
            ai_prediction = f"AI predicts completion by {completion_date}" if months_to_complete < 36 else "Long-term goal"
        else:
            ai_prediction = "Need more contributions to estimate"

        with col1 if i % 2 == 0 else col2:
            st.markdown(f"""
            <div style="padding: 1rem; background-color: #f8f9fa; border-radius: 10px; margin-bottom: 1rem;">
                <h4 style="margin-top: 0;">{goal["name"]}</h4>
                <p style="margin: 0;">€{goal["current"]:.2f} / €{goal["target"]:.2f}</p>
                <div class="progress-container" style="margin-top: 0.5rem;">
                    <div class="progress-bar" style="width: {progress}%; background-color: {PRIMARY_COLOR}"></div>
                </div>
                <p style="margin-top: 0.5rem; font-size: 0.8rem;">{ai_prediction}</p>
                <p style="margin-top: 0.5rem; font-size: 0.8rem;">Target date: {target_date}</p>
            </div>
            """, unsafe_allow_html=True)

    # AI Investment Projection
    st.markdown("<h3>AI Investment Projection</h3>", unsafe_allow_html=True)

    # Add some random investment data for demonstration
    if 'investment_projection' not in st.session_state:
        # Initial parameters
        current_amount = st.session_state.investments
        monthly_contribution = 100
        years = 5
        risk_level = 'medium'

        # Generate projections
        projection = predict_investment_returns(current_amount, monthly_contribution, years, risk_level)
        st.session_state.investment_projection = projection

    # Display the projection
    projection = st.session_state.investment_projection

    col1, col2 = st.columns([2, 1])

    with col1:
        # Create investment chart
        fig = px.line(
            x=projection['periods'] / 12,  # Convert to years
            y=projection['median_path'],
            labels={'x': 'Years', 'y': 'Portfolio Value (€)'},
            template='plotly_white'
        )

        # Add percentile lines
        fig.add_scatter(
            x=np.array([projection['periods'][-1] / 12]),
            y=np.array([projection['percentiles'][10]]),
            mode='markers',
            marker=dict(color='blue', size=10),
            name='Pessimistic (10%)'
        )

        fig.add_scatter(
            x=np.array([projection['periods'][-1] / 12]),
            y=np.array([projection['percentiles'][90]]),
            mode='markers',
            marker=dict(color='green', size=10),
            name='Optimistic (90%)'
        )

        fig.update_layout(
            margin=dict(t=30, b=30, l=30, r=30),
            height=300,
            title="Portfolio Growth Projection"
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown(f"""
        <div style="padding: 1rem; background-color: #f8f9fa; border-radius: 10px; height: 100%;">
            <h4 style="margin-top: 0;">AI Investment Forecast</h4>
            <p style="margin: 0;">Expected value in 5 years:</p>
            <h3 style="margin: 0;">€{projection['expected_value']:.2f}</h3>
            <p style="margin: 0;">Optimistic (90%): €{projection['percentiles'][90]:.2f}</p>
            <p style="margin: 0;">Pessimistic (10%): €{projection['percentiles'][10]:.2f}</p>
            <p style="margin-top: 1rem; font-size: 0.8rem;">Based on {risk_level} risk profile</p>
        </div>
        """, unsafe_allow_html=True)

    # Subscription upgrade recommendation based on ML model
    if 'subscription_recommender' in st.session_state.ml_models:
        # Get the recommendation model
        recommend_subscription = st.session_state.ml_models['subscription_recommender']

        # Sample parameters (in a real app, these would come from user data)
        monthly_income = 3000
        num_goals = len(st.session_state.goals)
        transaction_volume = len(st.session_state.transactions)
        savings_amount = st.session_state.savings
        investments_amount = st.session_state.investments

        # Get recommendation
        recommended_tier = recommend_subscription(
            monthly_income,
            num_goals,
            transaction_volume,
            savings_amount,
            investments_amount
        )

        # Only show if recommended tier is higher than current
        current_tier = st.session_state.subscription_tier
        tiers = ["Basic", "Pro", "Elite"]

        if tiers.index(recommended_tier) > tiers.index(current_tier):
            st.markdown("<h3>AI Subscription Recommendation</h3>", unsafe_allow_html=True)
            st.markdown(f"""
            <div style="padding: 1rem; background-color: #f0f7ff; border: 1px solid #cce5ff; border-radius: 10px; margin-top: 1rem;">
                <div style="display: flex; align-items: center; justify-content: space-between;">
                    <div>
                        <h4 style="margin-top: 0; color: #0366d6;">Upgrade Recommendation</h4>
                        <p style="margin: 0;">Our AI analysis suggests that the <strong>{recommended_tier} Plan</strong> would better suit your financial needs.</p>
                        <p style="margin-top: 0.5rem; font-size: 0.9rem;">Unlock advanced financial insights and planning tools.</p>
                    </div>
                    <div>
                        <button style="background-color: #0366d6; color: white; border: none; padding: 0.5rem 1rem; border-radius: 5px; cursor: pointer;">Upgrade Now</button>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            # AI-based budgeting advice
    st.markdown("<h3>Smart Budget Recommendations</h3>", unsafe_allow_html=True)

    # Check for spending patterns
    if len(st.session_state.transactions) > 10:
        # Calculate average spending by category
        category_spending = {}
        for transaction in st.session_state.transactions:
            category = transaction.get("category", "Other")
            amount = transaction.get("amount", 0)
            if amount < 0:  # Only count expenses
                category_spending[category] = category_spending.get(category, 0) + abs(amount)

        # Find top spending categories
        top_categories = sorted(category_spending.items(), key=lambda x: x[1], reverse=True)[:3]

        col1, col2 = st.columns([1, 1])

        with col1:
            st.markdown("""
            <div style="padding: 1rem; background-color: #f8f9fa; border-radius: 10px; margin-bottom: 1rem;">
                <h4 style="margin-top: 0;">Top Spending Categories</h4>
            """, unsafe_allow_html=True)

            for category, amount in top_categories:
                st.markdown(f"""
                <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                    <span>{category}</span>
                    <span>€{amount:.2f}</span>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True)

        with col2:
            # Budget optimization suggestion
            total_expenses = sum(abs(t["amount"]) for t in st.session_state.transactions if t["amount"] < 0)
            monthly_income = sum(t["amount"] for t in st.session_state.transactions if t["amount"] > 0)
            savings_rate = 0 if monthly_income == 0 else (monthly_income - total_expenses) / monthly_income

            st.markdown(f"""
            <div style="padding: 1rem; background-color: #f0f7ff; border-radius: 10px;">
                <h4 style="margin-top: 0;">AI Budget Insights</h4>
                <p style="margin: 0;">Your savings rate: <strong>{savings_rate:.1%}</strong></p>
                <p style="margin-top: 0.5rem;">
                    {"Great job! Your savings rate is healthy." if savings_rate > 0.2 else
                     "Consider reducing spending in your top categories to improve your savings rate."}
                </p>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Add more transactions to get personalized budget recommendations.")

    # Financial health score
    st.markdown("<h3>Financial Health Score</h3>", unsafe_allow_html=True)

    # Calculate a simple financial health score
    savings_balance = st.session_state.savings
    investment_balance = st.session_state.investments
    total_assets = savings_balance + investment_balance

    # Calculate emergency fund ratio (savings / monthly expenses)
    monthly_expenses = 0
    if len(st.session_state.transactions) > 0:
        expenses = [abs(t["amount"]) for t in st.session_state.transactions if t["amount"] < 0]
        if expenses:
            monthly_expenses = sum(expenses) / max(1, len(expenses) / 30)  # Approximate monthly expenses

    emergency_fund_ratio = 0 if monthly_expenses == 0 else savings_balance / monthly_expenses

    # Goals progress
    goals_progress = 0
    if st.session_state.goals:
        goal_progress_sum = sum(goal["current"] / max(1, goal["target"]) for goal in st.session_state.goals)
        goals_progress = goal_progress_sum / len(st.session_state.goals)

    # Calculate health score (0-100)
    health_score = min(100, max(0,
        20 * min(1, emergency_fund_ratio / 6) +  # 20 points for 6-month emergency fund
        40 * min(1, investment_balance / 10000) +  # 40 points for €10k investments
        40 * goals_progress  # 40 points for goals progress
    ))

    col1, col2 = st.columns([1, 2])

    with col1:
        # Display the score
        st.markdown(f"""
        <div style="padding: 1rem; background-color: #f8f9fa; border-radius: 10px; text-align: center;">
            <h4 style="margin-top: 0;">Your Score</h4>
            <div style="font-size: 3rem; font-weight: bold; color: {PRIMARY_COLOR};">{health_score:.0f}</div>
            <p style="margin: 0;">{
                "Excellent" if health_score >= 80 else
                "Good" if health_score >= 60 else
                "Fair" if health_score >= 40 else
                "Needs Improvement"
            }</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        # Show breakdown and improvement tips
        st.markdown(f"""
        <div style="padding: 1rem; background-color: #f8f9fa; border-radius: 10px;">
            <h4 style="margin-top: 0;">Score Breakdown</h4>
            <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                <span>Emergency Fund</span>
                <span>{min(20, 20 * min(1, emergency_fund_ratio / 6)):.0f}/20</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                <span>Investment Portfolio</span>
                <span>{min(40, 40 * min(1, investment_balance / 10000)):.0f}/40</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                <span>Goals Progress</span>
                <span>{min(40, 40 * goals_progress):.0f}/40</span>
            </div>
            <p style="margin-top: 1rem; font-size: 0.9rem;">
                {
                    "Keep up the great work! Consider increasing your investments for long-term growth." if health_score >= 80 else
                    "You're on the right track. Focus on building your emergency fund next." if health_score >= 60 else
                    "Consider setting up automatic transfers to your savings account." if health_score >= 40 else
                    "Start with a small emergency fund of €1,000 as your first financial goal."
                }
            </p>
        </div>
        """, unsafe_allow_html=True)

    # Financial education resources
    st.markdown("<h3>Learning Resources</h3>", unsafe_allow_html=True)

    # Display personalized educational resources based on needs
    resources = [
        {
            "title": "Emergency Fund Basics",
            "description": "Learn why and how to build your financial safety net",
            "url": "#",
            "tag": "Saving"
        },
        {
            "title": "Investment Fundamentals",
            "description": "Start your investment journey with these core concepts",
            "url": "#",
            "tag": "Investing"
        },
        {
            "title": "Budgeting Strategies",
            "description": "Simple techniques to manage your spending effectively",
            "url": "#",
            "tag": "Budgeting"
        }
    ]

    # Determine which resources to prioritize
    needed_tags = []
    if emergency_fund_ratio < 3:
        needed_tags.append("Saving")
    if investment_balance < 5000:
        needed_tags.append("Investing")
    if savings_rate < 0.1:
        needed_tags.append("Budgeting")

    # Sort resources by relevance
    sorted_resources = sorted(resources, key=lambda r: -1 if r["tag"] in needed_tags else 0)

    col1, col2, col3 = st.columns(3)
    cols = [col1, col2, col3]

    for i, resource in enumerate(sorted_resources[:3]):
        with cols[i]:
            is_priority = resource["tag"] in needed_tags
            bg_color = "#f0f7ff" if is_priority else "#f8f9fa"
            border = "1px solid #cce5ff" if is_priority else "none"

            st.markdown(f"""
            <div style="padding: 1rem; background-color: {bg_color}; border: {border}; border-radius: 10px; height: 100%;">
                <h4 style="margin-top: 0;">{resource["title"]}</h4>
                <p style="margin: 0;">{resource["description"]}</p>
                <div style="margin-top: 1rem;">
                    <a href="{resource["url"]}" style="text-decoration: none; color: {PRIMARY_COLOR};">Learn more →</a>
                </div>
                {f'<div style="margin-top: 0.5rem;"><span style="background-color: #e6f7ff; color: #0366d6; padding: 2px 8px; border-radius: 10px; font-size: 0.8rem;">Recommended</span></div>' if is_priority else ''}
            </div>
            """, unsafe_allow_html=True)

    # Footer
    st.markdown("""
    <div style="margin-top: 3rem; padding-top: 1rem; border-top: 1px solid #e6e6e6; text-align: center; color: #666;">
        <p style="font-size: 0.8rem;">
            FinanceAI Dashboard - Powered by StreamlitAI
        </p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
