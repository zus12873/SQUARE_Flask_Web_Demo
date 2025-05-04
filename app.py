import os,platform
from flask import Flask, Response, request, jsonify, render_template, redirect, url_for, flash
import subprocess
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_key_for_testing')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 初始化数据库
db = SQLAlchemy(app)

# 初始化登录管理器
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# 用户模型
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# 创建所有数据库表
with app.app_context():
    db.create_all()

@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('登录失败，请检查用户名和密码')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # 检查用户名是否已存在
        user = User.query.filter_by(username=username).first()
        if user:
            flash('用户名已存在')
            return render_template('register.html')
        
        # 检查密码是否匹配
        if password != confirm_password:
            flash('两次输入的密码不匹配')
            return render_template('register.html')
        
        # 创建新用户
        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        
        flash('注册成功，请登录')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/run_java_algorithm_stream', methods=['GET', 'POST'])
@login_required
def run_java_algorithm_stream():
    # 获取前端传入的参数（POST 的 JSON数据；GET时使用默认值）
    if request.method == 'POST' and request.is_json:
        data = request.get_json()
    else:
        data = {}
    # 获取参数
    estimation = data.get('estimation', 'supervised')
    dataset = data.get('dataset', 'HCB')
    nfold = data.get('nfold', 10)
    method = data.get('method', 'All') # Majority,Raykar,Bayes,Zen
    
    print(f"运行算法参数：estimation={estimation}, dataset={dataset}, nfold={nfold}, method={method}")

    # 确保目录存在
    if not os.path.exists('./data'):
        os.makedirs('./data', exist_ok=True)
    if not os.path.exists(f'./data/{dataset}'):
        os.makedirs(f'./data/{dataset}', exist_ok=True)

    # 根据监督方式构造配置文件及保存目录
    if estimation == "supervised":
        if nfold > 0:
            supervision_percentage = 100 / nfold
        else:
            supervision_percentage = 100 - (100 / abs(nfold))
        folder_name = "nFoldSet_" + str(supervision_percentage)
        saveDir = f"./nFoldSets/{dataset}/{method}/{estimation}/{folder_name}/"
        # 确保目录存在
        os.makedirs(saveDir, exist_ok=True)
        
        text_content = (
            f"--responses ./data/{dataset}/responses.txt "
            f"--category ./data/{dataset}/categories.txt "
            f"--groundTruth ./data/{dataset}/groundTruth.txt "
            f"--method {method} --nfold -{nfold} "
            f"--estimation {estimation} --saveDir {saveDir}"
        )
        text_file_name = f"genNFold{nfold}_{dataset}_{estimation}_{method}_CLA.txt"
    else:
        saveDir = f"./nFoldSets/{dataset}/{method}/{estimation}/"
        # 确保目录存在
        os.makedirs(saveDir, exist_ok=True)
        
        text_content = (
            f"--responses ./data/{dataset}/responses.txt "
            f"--category ./data/{dataset}/categories.txt "
            f"--groundTruth ./data/{dataset}/groundTruth.txt "
            f"--method {method} --estimation {estimation} --saveDir {saveDir}"
        )
        text_file_name = f"gen_{dataset}_{estimation}_{method}_CLA.txt"

    # 将配置内容写入文件
    with open(text_file_name, "w", encoding="utf-8") as file:
        file.write(text_content)
    print(f"内容已写入 {text_file_name}")

    # 构造 Java 命令
    sep = ';' if platform.system() == 'Windows' else ':'

    classpath = sep.join([
        'algorithm/jblas-1.2.4.jar',
        'algorithm/log4j-core-2.4.jar',
        'algorithm/log4j-api-2.4.jar',
        'algorithm/qa-2.0.jar'
    ])

    cmd = [
        'java',
        '-Xmx2048m',
        '-ea',
        '-cp',
        classpath,
        'org.square.qa.analysis.Main',
        '--file',
        text_file_name
    ]
    
    print(f"执行命令: {' '.join(cmd)}")
    
    def generate():
        # 启动 Java 进程，并实时输出日志
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
            for line in iter(process.stdout.readline, ''):
                print(f"Java输出: {line.strip()}")
                yield f"data: {line}\n\n"
            process.stdout.close()
            return_code = process.wait()
            print(f"进程结束，返回码: {return_code}")
            yield f"data: Process finished with return code {return_code}\n\n"
        except Exception as e:
            error_msg = f"启动进程时出错: {str(e)}"
            print(error_msg)
            yield f"data: ERROR: {error_msg}\n\n"
            yield f"data: Process finished with return code -1\n\n"
    
    return Response(generate(), mimetype='text/event-stream')


@app.route('/get_evaluation_results', methods=['POST'])
@login_required
def get_evaluation_results():
    """
    该接口根据前端传入的参数读取结果文件夹下所有 .txt 文件，
    提取文件名中的评分方法，并解析文件内容，将数据打包成 JSON 返回给前端。
    """
    data = request.get_json() or {}
    estimation = data.get('estimation', 'supervised')
    dataset = data.get('dataset', 'HCB')
    nfold = data.get('nfold', 10)
    method = data.get('method', 'All')
    print(f"评估参数：estimation={estimation}, dataset={dataset}, nfold={nfold}, method={method}")
    
    # 构造结果文件夹路径
    if estimation == "supervised":
        if nfold > 0:
            supervision_percentage = 100 / nfold
        else:
            supervision_percentage = 100 - (100 / abs(nfold))
        results_folder = f"./nFoldSets/{dataset}/{method}/{estimation}/nFoldSet_{supervision_percentage}/results/nFold"
        print(f"结果文件夹路径: {results_folder}")
    else:
        results_folder = f"./nFoldSets/{dataset}/{method}/{estimation}/results/nFold"
        print(f"结果文件夹路径: {results_folder}")
    
    # 检查结果文件夹是否存在
    if not os.path.exists(results_folder):
        # 尝试查找其他可能的路径
        alternative_folders = [
            f"./nFoldSets/{dataset}/{estimation}/nFoldSet_{supervision_percentage if 'supervision_percentage' in locals() else ''}/results/nFold",
            f"./nFoldSets/{dataset}/{estimation}/results/nFold",
            f"./nFoldSets/{dataset}/All/{estimation}/nFoldSet_{supervision_percentage if 'supervision_percentage' in locals() else ''}/results/nFold",
            f"./nFoldSets/{dataset}/All/{estimation}/results/nFold"
        ]
        
        for alt_folder in alternative_folders:
            print(f"尝试替代路径: {alt_folder}")
            if os.path.exists(alt_folder):
                results_folder = alt_folder
                print(f"找到替代路径: {results_folder}")
                break
        else:
            print(f"错误：结果文件夹 {results_folder} 不存在，且未找到替代路径")
            return jsonify({"error": f"结果文件夹不存在: {results_folder}。请确保算法已成功运行。"}), 404
    
    results = []
    try:
        files = os.listdir(results_folder)
        print(f"文件夹 {results_folder} 中的文件: {files}")
        
        for filename in files:
            if filename.endswith('.txt'):
                # 提取文件名中评分方法部分（例如 "Majority_unsupervised_results.txt" 提取 "Majority"）
                method_name = filename.split('_')[0]
                file_path = os.path.join(results_folder, filename)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        lines = [line.strip() for line in content.splitlines() if line.strip()]
                        # 分别获取以 "%" 开头的 header 行和其它数据行
                        headers = [line for line in lines if line.startswith('%')]
                        data_lines = [line for line in lines if not line.startswith('%')]
                    
                    print(f"文件 {filename} 读取成功，header行数: {len(headers)}, 数据行数: {len(data_lines)}")
                    results.append({
                        "method": method_name,
                        "filename": filename,
                        "headers": headers,
                        "data": data_lines
                    })
                except Exception as e:
                    print(f"读取文件 {filename} 时出错: {str(e)}")
                    results.append({
                        "method": method_name,
                        "filename": filename,
                        "error": str(e)
                    })
        
        if not results:
            print(f"警告：文件夹 {results_folder} 中没有找到任何 .txt 文件")
            return jsonify({"warning": f"文件夹 {results_folder} 中没有找到任何结果文件"}), 200
        
        return jsonify({"results": results})
    except Exception as e:
        print(f"处理结果时出错: {str(e)}")
        return jsonify({"error": f"处理结果时出错: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)
