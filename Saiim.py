from flask import Flask, request, render_template_string
import requests, time, random
from datetime import datetime, timedelta

app = Flask(__name__)

HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>FB Auto Commenter</title>
    <style>
        body { font-family: Arial, sans-serif; background: #f5f5f5; padding: 20px; }
        .container { max-width: 600px; margin: auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 0 10px #ccc; }
        textarea, input[type=text], input[type=number] { width: 100%; padding: 10px; margin-bottom: 10px; }
        button { padding: 10px 20px; background: green; color: white; border: none; border-radius: 5px; cursor: pointer; }
        .log { white-space: pre-wrap; background: #eee; padding: 10px; height: 300px; overflow-y: scroll; }
    </style>
</head>
<body>
<div class="container">
    <h2>Facebook Auto Commenter (Flask)</h2>
    <form method="POST">
        <label>Access Tokens (one per line):</label>
        <textarea name="tokens" rows="5"></textarea>

        <label>Post IDs (one per line):</label>
        <textarea name="posts" rows="3"></textarea>

        <label>Comments (Spintax format supported):</label>
        <textarea name="comments" rows="5"></textarea>

        <label>Delay (seconds):</label>
        <input type="number" name="delay" value="60" min="10">

        <label>Haters Name (prefix):</label>
        <input type="text" name="haters">

        <label>Append 'here' at end?</label>
        <input type="checkbox" name="here" checked>

        <button type="submit">Start Commenting</button>
    </form>
    {% if log %}
    <h3>Logs:</h3>
    <div class="log">{{ log }}</div>
    {% endif %}
</div>
</body>
</html>
'''

def random_comment(template):
    while '{' in template:
        start = template.find('{')
        end = template.find('}')
        options = template[start+1:end].split('|')
        template = template[:start] + random.choice(options) + template[end+1:]
    return template

@app.route('/', methods=['GET', 'POST'])
def index():
    log = ""
    if request.method == 'POST':
        tokens = request.form['tokens'].strip().splitlines()
        posts = request.form['posts'].strip().splitlines()
        comments = request.form['comments'].strip().splitlines()
        delay = int(request.form['delay'])
        haters = request.form['haters'].strip()
        add_here = 'here' in request.form

        cooldown = {t: datetime.min for t in tokens}
        success = 0
        i = 0

        while tokens:
            now = datetime.now()
            available = [t for t in tokens if now >= cooldown[t]]
            if not available:
                log += f"[WAIT] All tokens cooling down...\n"
                time.sleep(5)
                continue

            token = available[i % len(available)]
            comment = random_comment(random.choice(comments))
            message = f"{haters} {comment}"
            if add_here:
                message += " here"
            post_id = random.choice(posts)

            res = requests.post(f"https://graph.facebook.com/{post_id}/comments", data={
                'message': message,
                'access_token': token
            }).json()

            if 'id' in res:
                success += 1
                log += f"[{datetime.now().strftime('%H:%M:%S')}] ✅ {message}\n"
            else:
                error = res.get('error', {}).get('message', 'Unknown error')
                log += f"[{datetime.now().strftime('%H:%M:%S')}] ❌ {error}\n"
                if 'invalid' in error or 'session' in error:
                    tokens.remove(token)
                    cooldown.pop(token, None)
                    log += f"❌ Token removed. {len(tokens)} left.\n"
                    continue
                cooldown[token] = datetime.now() + timedelta(minutes=15)
            time.sleep(delay)
            i += 1
            if i > 20:
                break  # Limit for browser run

    return render_template_string(HTML, log=log)

if __name__ == '__main__':
    app.run(debug=True)
