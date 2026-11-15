
from flask import Flask, render_template, request, jsonify, Response
import sqlite3
import csv
import io
from datetime import date, datetime, timedelta

app = Flask(__name__)

DATABASE = "feedback.db"


# 1. DATABASE CONNECTION
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# 2. CREATE DATABASE TABLE
def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT,
            category TEXT NOT NULL,
            rating INTEGER NOT NULL,
            comment TEXT NOT NULL,
            sentiment TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


# 3. SENTIMENT ANALYSIS
def analyze_sentiment(comment):
    positive_words = [
        "good", "great", "excellent", "helpful",
        "clear", "amazing", "best", "love",
        "interesting", "easy", "wonderful",
        "appreciate", "thank"
    ]

    negative_words = [
        "bad", "poor", "difficult", "boring",
        "confusing", "slow", "problem", "worst",
        "hate", "unclear", "hard", "improve"
    ]

    text = comment.lower()

    positive_count = sum(
        1 for word in positive_words if word in text
    )

    negative_count = sum(
        1 for word in negative_words if word in text
    )

    if positive_count > negative_count:
        return "Positive"
    elif negative_count > positive_count:
        return "Negative"
    else:
        return "Neutral"


# 4. HOME PAGE
@app.route("/")
def home():
    return render_template("index.html")


# 5. SUBMIT FEEDBACK
@app.route("/api/feedback", methods=["POST"])
def submit_feedback():
    data = request.get_json(silent=True) or request.form

    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip()
    category = str(data.get("category", "")).strip()
    comment = str(data.get("comment", "")).strip()

    try:
        rating = int(data.get("rating", 0))
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid rating"}), 400

    if not name or not category or not comment:
        return jsonify({
            "error": "Please fill in all required fields"
        }), 400

    if rating < 1 or rating > 5:
        return jsonify({
            "error": "Rating must be between 1 and 5"
        }), 400

    sentiment = analyze_sentiment(comment)
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_db()

    conn.execute("""
        INSERT INTO feedback
        (name, email, category, rating, comment, sentiment, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        name,
        email,
        category,
        rating,
        comment,
        sentiment,
        created_at
    ))

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Feedback submitted successfully!",
        "sentiment": sentiment
    }), 201


# 6. DASHBOARD DATA
@app.route("/api/dashboard")
def dashboard():
    conn = get_db()

    total = conn.execute(
        "SELECT COUNT(*) FROM feedback"
    ).fetchone()[0]

    average_rating = conn.execute(
        "SELECT AVG(rating) FROM feedback"
    ).fetchone()[0] or 0

    positive_count = conn.execute("""
        SELECT COUNT(*) FROM feedback
        WHERE sentiment = 'Positive'
    """).fetchone()[0]

    positive_rate = (
        positive_count / total * 100 if total else 0
    )

    categories = conn.execute("""
        SELECT category, COUNT(*) AS count
        FROM feedback
        GROUP BY category
        ORDER BY count DESC
    """).fetchall()

    recent = conn.execute("""
        SELECT id, name, category, rating,
               comment, sentiment, created_at
        FROM feedback
        ORDER BY id DESC
        LIMIT 10
    """).fetchall()

    trend = []

    for days_ago in range(6, -1, -1):
        target_date = date.today() - timedelta(days=days_ago)

        count = conn.execute("""
            SELECT COUNT(*) FROM feedback
            WHERE DATE(created_at) = ?
        """, (target_date.isoformat(),)).fetchone()[0]

        trend.append({
            "date": target_date.strftime("%d %b"),
            "count": count
        })

    conn.close()

    return jsonify({
        "total": total,
        "average_rating": round(average_rating, 2),
        "positive_rate": round(positive_rate, 1),
        "categories": [dict(row) for row in categories],
        "recent": [dict(row) for row in recent],
        "trend": trend
    })


# 7. FEEDBACK INSIGHTS
@app.route("/api/insights")
def insights():
    conn = get_db()

    sentiment_rows = conn.execute("""
        SELECT sentiment, COUNT(*) AS count
        FROM feedback
        GROUP BY sentiment
    """).fetchall()

    sentiment_counts = {
        "Positive": 0,
        "Negative": 0,
        "Neutral": 0
    }

    for row in sentiment_rows:
        sentiment_counts[row["sentiment"]] = row["count"]

    low_ratings = conn.execute("""
        SELECT name, category, rating, comment
        FROM feedback
        WHERE rating <= 2
        ORDER BY id DESC
        LIMIT 10
    """).fetchall()

    top_category = conn.execute("""
        SELECT category, COUNT(*) AS count
        FROM feedback
        GROUP BY category
        ORDER BY count DESC
        LIMIT 1
    """).fetchone()

    total = conn.execute(
        "SELECT COUNT(*) FROM feedback"
    ).fetchone()[0]

    conn.close()

    if total == 0:
        message = "No feedback received yet."
    elif sentiment_counts["Negative"] > sentiment_counts["Positive"]:
        message = (
            "More negative feedback received. "
            "Review student concerns and improve teaching methods."
        )
    elif sentiment_counts["Positive"] > sentiment_counts["Negative"]:
        message = (
            "Students shared more positive feedback. "
            "Continue the practices they appreciate."
        )
    else:
        message = (
            "Feedback is mixed. Review student comments "
            "to identify areas for improvement."
        )

    return jsonify({
        "sentiment_counts": sentiment_counts,
        "low_ratings": [dict(row) for row in low_ratings],
        "top_category": dict(top_category) if top_category else None,
        "message": message
    })


# 8. EXPORT FEEDBACK TO CSV
@app.route("/api/export")
def export_feedback():
    conn = get_db()

    rows = conn.execute("""
        SELECT id, name, email, category, rating,
               comment, sentiment, created_at
        FROM feedback
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "ID", "Name", "Email", "Category",
        "Rating", "Comment", "Sentiment", "Created At"
    ])

    for row in rows:
        writer.writerow([
            row["id"],
            row["name"],
            row["email"],
            row["category"],
            row["rating"],
            row["comment"],
            row["sentiment"],
            row["created_at"]
        ])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition":
            "attachment; filename=student_feedback.csv"
        }
    )


# 9. RUN APPLICATION
if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5001, debug=True)
