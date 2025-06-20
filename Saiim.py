from flask import Flask, request, render_template_string, redirect
import requests, time, random, threading, os
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>FB Auto Commenter</title>
    <style>
        body { font-family: Arial, sans-serif; background: #f0f0f0; padding: 20px; }
        .container { max-width: 600px; margin: auto; background: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 0 10px #ccc; }
        input, textarea, button, label { width: 100%; margin: 8px 0; }
        button { background: green; color: white; border: none; padding: 10px; border-radius: 5px; cursor: pointer; }
        .log { white-space: pre-wrap; background: #eee; padding: 10px; height: 300px; overflow-y: scroll; }
    </style>
</head>
<body>
<div class="container">
    <h2>Facebook Auto Commenter</h2>
    <form method="POST" enctype="multipart/form-data">
        <label>Upload Token File:</label>
        <input type="file" name="token_file" required>

        <label>Upload Comments File:</label>
        <input type="file" name="comment_file" required>

        <label>Post IDs (comma separated):</label>
        <input type="text" name="posts" required>

        <label>Delay in seconds:</label>
        <input type="number" name="delay" value="60" required>

        <label>Haters Name (prefix):</label>
        <input type="text" name="haters">

        <label>Append 'here' at end?</label>
        <input type="checkbox" name="here" checked>

        <button name="action" value="start">Start Commenting</button>
        <button name="action" value="stop" style="background:red;">Stop Bot</button>
    </form>
    {% if log %}
    <h3>Logs:</h3>
    <div class="log">{{ log }}</div>
    {% endif %}
</div>
</body>
</html>
'''

running = False
thread = None


def read_file(file):
    return [line.strip() for line in file.read().decode("utf-8").splitlines() if line.strip()]

def random_comment(template):
    while '{' in template:
        start = template.find('{')
        end = template.find('}')
        options = template[start+1:end].split('|')
        template = template[:start] + random.choice(options) + template[end+1:]
    return template

def comment_worker(tokens, comments, post_ids, delay, haters, add_here):
    global running
    cooldown = {t: datetime.min for t in tokens}
    success = 0
    i = 0
    log_output = ""

    while running and tokens:
        now = datetime.now()
        available = [t for t in tokens if now >= cooldown[t]]
        if not available:
            time.sleep(3)
            continue

        token = available[i % len(available)]
        comment = random_comment(random.choice(comments))
        message = f"{haters} {comment}"
        if add_here:
            message += " here"

        post_id = random.choice(post_ids)
        res = requests.post(f"https://graph.facebook.com/{post_id}/comments", data={
            'message': message,
            'access_token': token
        }).json()

        if 'id' in res:
            success += 1
            print(f"✅ {message}")
        else:
            error = res.get('error', {}).get('message', 'Unknown error')
            print(f"❌ {error}")
            if 'invalid' in error or 'session' in error:
                tokens.remove(token)
                cooldown.pop(token, None)
                continue
            cooldown[token] = datetime.now() + timedelta(minutes=15)

        time.sleep(delay)
        i += 1

@app.route('/', methods=['GET', 'POST'])
def index():
    global running, thread
    log = ""
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'stop':
            running = False
            return render_template_string(HTML, log="⛔ Bot Stopped.")

        try:
            token_file = request.files['token_file']
            comment_file = request.files['comment_file']
            tokens = read_file(token_file)
            comments = read_file(comment_file)
            post_ids = request.form['posts'].split(',')
            delay = int(request.form['delay'])
            haters = request.form['haters']
            add_here = 'here' in request.form

            running = True
            thread = threading.Thread(target=comment_worker, args=(tokens, comments, post_ids, delay, haters, add_here))
            thread.start()
            return render_template_string(HTML, log="🚀 Bot Started...")
        except Exception as e:
            return render_template_string(HTML, log=f"❌ Error: {str(e)}")
    return render_template_string(HTML, log="")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
