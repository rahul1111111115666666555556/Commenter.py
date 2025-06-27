from flask import Flask, request, render_template_string
import requests, time, threading, os
from datetime import datetime

app = Flask(__name__)
HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>FB Page Auto Commenter</title>
    <style>
        body { font-family: Arial; background: #f5f5f5; padding: 20px; }
        .container { background: white; padding: 20px; border-radius: 10px; max-width: 600px; margin: auto; box-shadow: 0 0 10px #ccc; }
        input, textarea, button { width: 100%; margin: 10px 0; padding: 10px; }
        button { background: green; color: white; border: none; border-radius: 5px; cursor: pointer; }
        .log { background: #eee; padding: 10px; white-space: pre-wrap; height: 300px; overflow-y: scroll; border-radius: 5px; }
    </style>
</head>
<body>
<div class="container">
    <h2>Facebook Page Auto Commenter</h2>
    <form method="POST" enctype="multipart/form-data">
        <label>Upload Token File:</label>
        <input type="file" name="token_file" required>

        <label>Upload Comments File:</label>
        <input type="file" name="comment_file" required>

        <label>Post IDs (comma-separated):</label>
        <input type="text" name="posts" required>

        <label>Delay (seconds):</label>
        <input type="number" name="delay" value="30">

        <button name="action" value="start">Start Commenting</button>
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
def read_lines(file):
    return [line.strip() for line in file.read().decode("utf-8").splitlines() if line.strip()]

def get_user_name(token):
    res = requests.get('https://graph.facebook.com/me', params={ 'access_token': token }).json()
    return res.get('name', 'Unknown')

def get_pages(token):
    res = requests.get('https://graph.facebook.com/me/accounts', params={ 'access_token': token }).json()
    return res.get('data', [])

def post_comment(page_token, post_id, message):
    res = requests.post(f'https://graph.facebook.com/{post_id}/comments', data={
        'message': message,
        'access_token': page_token
    }).json()
    return res

def comment_worker(tokens, comments, post_ids, delay, log_list):
    for token in tokens:
        name = get_user_name(token)
        pages = get_pages(token)
        if not pages:
            log_list.append(f"❌ {name} = No pages found")
            continue
        log_list.append(f"✅ {name} = {len(pages)} page found")
        for page in pages:
            page_name = page.get('name')
            page_token = page.get('access_token')
            comment = random.choice(comments)
            post_id = random.choice(post_ids)
            res = post_comment(page_token, post_id, comment)
            if 'id' in res:
                log_list.append(f"✅ Comment posted by {page_name} to {post_id}")
            else:
                error = res.get('error', {}).get('message', 'Unknown error')
                log_list.append(f"❌ Failed by {page_name}: {error}")
            time.sleep(delay)

@app.route('/', methods=['GET', 'POST'])
def index():
    global running
    log = []
    if request.method == 'POST':
        try:
            token_file = request.files['token_file']
            comment_file = request.files['comment_file']
            tokens = read_lines(token_file)
            comments = read_lines(comment_file)
            post_ids = [p.strip() for p in request.form['posts'].split(',') if p.strip()]
            delay = int(request.form.get('delay', 30))

            running = True
            thread = threading.Thread(target=comment_worker, args=(tokens, comments, post_ids, delay, log))
            thread.start()
            thread.join()
        except Exception as e:
            log.append(f"❌ Error: {str(e)}")
    return render_template_string(HTML, log='\n'.join(log))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
