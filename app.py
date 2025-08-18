from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

import sqlite3

from werkzeug.exceptions import abort
from werkzeug.security import generate_password_hash, check_password_hash
from jinja2 import Environment
# from kage-sama import criar_usuario_admin



app = Flask(__name__)
app.jinja_env.globals.update(zip=zip)
app.secret_key = 'Ehqb_E._Uhlv_LL'

# -------------------------------------------------------- Configuração do Flask-Login



login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    pass

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    user_data = conn.execute('SELECT * FROM usuarios WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    
    if not user_data:
        return None
    
    user = User()
    user.id = user_data['id']
    user.username = user_data['username']
    user.is_admin = user_data['is_admin']
    return user



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        user_data = conn.execute(
            'SELECT * FROM usuarios WHERE username = ?', (username,)
        ).fetchone()
        conn.close()
        
        if user_data and check_password_hash(user_data['password_hash'], password):
            user = User()
            user.id = user_data['id']
            login_user(user)
            return redirect(url_for('index'))
        
        flash('Credenciais inválidas!')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/criar-conta', methods=['GET', 'POST'])
def criar_conta():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        is_admin = 1 if request.form.get('is_admin') else 0
        
        conn = get_db_connection()
        try:
            conn.execute(
                'INSERT INTO usuarios (username, password_hash, is_admin) VALUES (?, ?, ?)',
                (username, generate_password_hash(password), is_admin)
            )
            conn.commit()
            flash('Conta criada com sucesso!')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Usuário já existe!')
        finally:
            conn.close()
    
    return render_template('criar_conta.html')



# -------------------------------------------------------- END Configuração do Flask-Login




# -------------------------------------------------------- Configuração do banco de dados
def get_db_connection():
    conn = sqlite3.connect('alunos.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    
    # Cria tabela de alunos (se já não existir)
    conn.execute('''
    CREATE TABLE IF NOT EXISTS alunos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        email TEXT NOT NULL,
        telefone TEXT,
        curso TEXT,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    
    conn.execute('''
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        is_admin BOOLEAN DEFAULT 0
    )
    ''')
    
    conn.commit()
    conn.close()
# -------------------------------------------------------- END Configuração do banco de dados


@app.route('/')
def index():
    search_term = request.args.get('search', '').strip()
    conn = get_db_connection()
    
    if search_term:
        alunos = conn.execute(
            'SELECT * FROM alunos WHERE nome LIKE ? OR email LIKE ? OR curso LIKE ?',
            (f'%{search_term}%', f'%{search_term}%', f'%{search_term}%')
        ).fetchall()
    else:
        alunos = conn.execute('SELECT * FROM alunos').fetchall()
    
    conn.close()
    return render_template('index.html', alunos=alunos, search_term=search_term)



# Rota para visualizar detalhes de um aluno
@app.route('/<int:id>')
def ver_aluno(id):
    conn = get_db_connection()
    aluno = conn.execute('SELECT * FROM alunos WHERE id = ?', (id,)).fetchone()
    conn.close()
    if aluno is None:
        abort(404)
    return render_template('ver.html', aluno=aluno)



# ----------------------------------------------------- Rota CRUDs  aluno
@app.route('/adicionar', methods=('GET', 'POST'))
@login_required
def adicionar():
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        telefone = request.form['telefone']
        curso = request.form['curso']

        if not nome or not email:
            flash('Nome e email são obrigatórios!')
        else:
            conn = get_db_connection()
            conn.execute('INSERT INTO alunos (nome, email, telefone, curso) VALUES (?, ?, ?, ?)',
                         (nome, email, telefone, curso))
            conn.commit()
            conn.close()
            flash('Aluno adicionado com sucesso!')
            return redirect(url_for('index'))

    return render_template('adicionar.html')


@app.route('/<int:id>/editar', methods=('GET', 'POST'))
@login_required
def editar(id):
    conn = get_db_connection()
    aluno = conn.execute('SELECT * FROM alunos WHERE id = ?', (id,)).fetchone()

    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        telefone = request.form['telefone']
        curso = request.form['curso']

        if not nome or not email:
            flash('Nome e email são obrigatórios!')
        else:
            conn.execute('UPDATE alunos SET nome = ?, email = ?, telefone = ?, curso = ? WHERE id = ?',
                        (nome, email, telefone, curso, id))
            conn.commit()
            conn.close()
            flash('Aluno atualizado com sucesso!')
            return redirect(url_for('index'))

    conn.close()
    return render_template('editar.html', aluno=aluno)


@app.route('/<int:id>/deletar', methods=('POST',))
@login_required
def deletar(id):
    if not current_user.is_admin:
        abort(403)
    conn = get_db_connection()
    aluno = conn.execute('SELECT * FROM alunos WHERE id = ?', (id,)).fetchone()
    if aluno is None:
        abort(404)
    conn.execute('DELETE FROM alunos WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash('Aluno deletado com sucesso!')
    return redirect(url_for('index'))

# ----------------------------------------------------- END Rota CRUDs  aluno


@app.route('/estatisticas')
def estatisticas():
    conn = get_db_connection()
    
    # Obtém contagem de alunos por curso
    cursos = conn.execute('''
        SELECT curso, COUNT(*) as total 
        FROM alunos 
        GROUP BY curso 
        ORDER BY total DESC
    ''').fetchall()
    
    conn.close()
    
    # Prepara os dados para o gráfico
    labels = [curso['curso'] if curso['curso'] else 'Não informado' for curso in cursos]
    valores = [curso['total'] for curso in cursos]
    
    return render_template('estatisticas.html', 
                        labels=labels, 
                        valores=valores,
                        total_alunos=sum(valores))


def popular_banco_dados():
    conn = get_db_connection()
    
    # Cria a tabela se não existir
    conn.execute('''
    CREATE TABLE IF NOT EXISTS alunos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        email TEXT NOT NULL,
        telefone TEXT,
        curso TEXT,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # if table == null or table == 0 
    count = conn.execute('SELECT COUNT(*) FROM alunos').fetchone()[0]
    
    if count == 0:
        estudantes = [
            ('João Silva', 'joao.silva@email.com', '(11) 98765-4321', 'Engenharia de Software'),
            ('Maria Oliveira', 'maria.oliveira@email.com', '(11) 98765-4322', 'Ciência da Computação'),
            ('Carlos Souza', 'carlos.souza@email.com', '(11) 98765-4323', 'Sistemas de Informação'),
            ('Ana Costa', 'ana.costa@email.com', '(11) 98765-4324', 'Engenharia da Computação'),
            ('Pedro Santos', 'pedro.santos@email.com', '(11) 98765-4325', 'Análise de Sistemas'),
            ('Juliana Pereira', 'juliana.pereira@email.com', '(11) 98765-4326', 'Engenharia de Software'),
            ('Marcos Lima', 'marcos.lima@email.com', '(11) 98765-4327', 'Ciência da Computação'),
            ('Fernanda Rocha', 'fernanda.rocha@email.com', '(11) 98765-4328', 'Sistemas de Informação'),
            ('Ricardo Alves', 'ricardo.alves@email.com', '(11) 98765-4329', 'Engenharia da Computação'),
            ('Patrícia Gomes', 'patricia.gomes@email.com', '(11) 98765-4330', 'Análise de Sistemas'),
            ('Lucas Martins', 'lucas.martins@email.com', '(11) 98765-4331', 'Engenharia de Software'),
            ('Amanda Barbosa', 'amanda.barbosa@email.com', '(11) 98765-4332', 'Ciência da Computação'),
            ('Gustavo Ferreira', 'gustavo.ferreira@email.com', '(11) 98765-4333', 'Sistemas de Informação'),
            ('Isabela Ribeiro', 'isabela.ribeiro@email.com', '(11) 98765-4334', 'Engenharia da Computação'),
            ('Roberto Carvalho', 'roberto.carvalho@email.com', '(11) 98765-4335', 'Análise de Sistemas'),
            ('Tatiane Nunes', 'tatiane.nunes@email.com', '(11) 98765-4336', 'Engenharia de Software'),
            ('Felipe Cunha', 'felipe.cunha@email.com', '(11) 98765-4337', 'Ciência da Computação'),
            ('Vanessa Dias', 'vanessa.dias@email.com', '(11) 98765-4338', 'Sistemas de Informação'),
            ('Eduardo Mendes', 'eduardo.mendes@email.com', '(11) 98765-4339', 'Engenharia da Computação'),
            ('Laura Moreira', 'laura.moreira@email.com', '(11) 98765-4340', 'Análise de Sistemas'),
            ('Rodrigo Cardoso', 'rodrigo.cardoso@email.com', '(11) 98765-4341', 'Engenharia de Software'),
            ('Beatriz Xavier', 'beatriz.xavier@email.com', '(11) 98765-4342', 'Ciência da Computação'),
            ('Daniel Teixeira', 'daniel.teixeira@email.com', '(11) 98765-4343', 'Sistemas de Informação'),
            ('Camila Andrade', 'camila.andrade@email.com', '(11) 98765-4344', 'Engenharia da Computação'),
            ('Marcelo Castro', 'marcelo.castro@email.com', '(11) 98765-4345', 'Análise de Sistemas'),
            ('Renata Duarte', 'renata.duarte@email.com', '(11) 98765-4346', 'Engenharia de Software'),
            ('Alexandre Fonseca', 'alexandre.fonseca@email.com', '(11) 98765-4347', 'Ciência da Computação'),
            ('Simone Guimarães', 'simone.guimaraes@email.com', '(11) 98765-4348', 'Sistemas de Informação'),
            ('Hugo Lopes', 'hugo.lopes@email.com', '(11) 98765-4349', 'Engenharia da Computação'),
            ('Elaine Macedo', 'elaine.macedo@email.com', '(11) 98765-4350', 'Análise de Sistemas'),
            ('André Neves', 'andre.neves@email.com', '(11) 98765-4351', 'Engenharia de Software'),
            ('Cristina Pires', 'cristina.pires@email.com', '(11) 98765-4352', 'Ciência da Computação'),
            ('Sérgio Queiroz', 'sergio.queiroz@email.com', '(11) 98765-4353', 'Sistemas de Informação'),
            ('Larissa Ramos', 'larissa.ramos@email.com', '(11) 98765-4354', 'Engenharia da Computação'),
            ('Paulo Soares', 'paulo.soares@email.com', '(11) 98765-4355', 'Análise de Sistemas'),
            ('Mônica Torres', 'monica.torres@email.com', '(11) 98765-4356', 'Engenharia de Software'),
            ('Rafael Uchôa', 'rafael.uchoa@email.com', '(11) 98765-4357', 'Ciência da Computação'),
            ('Viviane Vasconcelos', 'viviane.vasconcelos@email.com', '(11) 98765-4358', 'Sistemas de Informação'),
            ('Diego Wernick', 'diego.wernick@email.com', '(11) 98765-4359', 'Engenharia da Computação'),
            ('Helena Yamasaki', 'helena.yamasaki@email.com', '(11) 98765-4360', 'Análise de Sistemas'),
            ('Bruno Zanetti', 'bruno.zanetti@email.com', '(11) 98765-4361', 'Engenharia de Software'),
            ('Adriana Albuquerque', 'adriana.albuquerque@email.com', '(11) 98765-4362', 'Ciência da Computação'),
            ('Otávio Brito', 'otavio.brito@email.com', '(11) 98765-4363', 'Sistemas de Informação'),
            ('Natália Correia', 'natalia.correia@email.com', '(11) 98765-4364', 'Engenharia da Computação'),
            ('Leonardo Dantas', 'leonardo.dantas@email.com', '(11) 98765-4365', 'Análise de Sistemas'),
            ('Débora Esteves', 'debora.esteves@email.com', '(11) 98765-4366', 'Engenharia de Software'),
            ('Fábio Fontes', 'fabio.fontes@email.com', '(11) 98765-4367', 'Ciência da Computação'),
            ('Gabriela Guedes', 'gabriela.guedes@email.com', '(11) 98765-4368', 'Sistemas de Informação'),
            ('Igor Holanda', 'igor.holanda@email.com', '(11) 98765-4369', 'Engenharia da Computação'),
            ('Jéssica Ilha', 'jessica.ilha@email.com', '(11) 98765-4370', 'Análise de Sistemas'),
            ('Thiago Azevedo', 'thiago.azevedo@email.com', '(11) 98765-4371', 'Engenharia de Software'),
            ('Melissa Cardoso', 'melissa.cardoso@email.com', '(11) 98765-4372', 'Ciência da Computação'),
            ('Cláudio Batista', 'claudio.batista@email.com', '(11) 98765-4373', 'Sistemas de Informação'),
            ('Priscila Farias', 'priscila.farias@email.com', '(11) 98765-4374', 'Engenharia da Computação'),
            ('Vitor Nogueira', 'vitor.nogueira@email.com', '(11) 98765-4375', 'Análise de Sistemas'),
            ('Carolina Teles', 'carolina.teles@email.com', '(11) 98765-4376', 'Engenharia de Software'),
            ('Rogério Peixoto', 'rogerio.peixoto@email.com', '(11) 98765-4377', 'Ciência da Computação'),
            ('Tatiana Braga', 'tatiana.braga@email.com', '(11) 98765-4378', 'Sistemas de Informação'),
            ('Márcio Correia', 'marcio.correia@email.com', '(11) 98765-4379', 'Engenharia da Computação'),
            ('Clara Martins', 'clara.martins@email.com', '(11) 98765-4380', 'Análise de Sistemas'),
            ('Henrique Duarte', 'henrique.duarte@email.com', '(11) 98765-4381', 'Engenharia de Software'),
            ('Aline Ferreira', 'aline.ferreira@email.com', '(11) 98765-4382', 'Ciência da Computação'),
            ('Samuel Barros', 'samuel.barros@email.com', '(11) 98765-4383', 'Sistemas de Informação'),
            ('Mirela Rocha', 'mirela.rocha@email.com', '(11) 98765-4384', 'Engenharia da Computação'),
            ('Edson Lima', 'edson.lima@email.com', '(11) 98765-4385', 'Análise de Sistemas'),
            ('Paula Menezes', 'paula.menezes@email.com', '(11) 98765-4386', 'Engenharia de Software'),
            ('Luiz Fernando', 'luiz.fernando@email.com', '(11) 98765-4387', 'Ciência da Computação'),
            ('Célia Ramos', 'celia.ramos@email.com', '(11) 98765-4388', 'Sistemas de Informação'),
            ('Jonas Carvalho', 'jonas.carvalho@email.com', '(11) 98765-4389', 'Engenharia da Computação'),
            ('Bianca Moraes', 'bianca.moraes@email.com', '(11) 98765-4390', 'Análise de Sistemas'),
            ('Fernando Silveira', 'fernando.silveira@email.com', '(11) 98765-4391', 'Engenharia de Software'),
            ('Patrícia Lemos', 'patricia.lemos@email.com', '(11) 98765-4392', 'Ciência da Computação'),
            ('Rafael Duarte', 'rafael.duarte2@email.com', '(11) 98765-4393', 'Sistemas de Informação'),
            ('Isis Moreira', 'isis.moreira@email.com', '(11) 98765-4394', 'Engenharia da Computação'),
            ('Marcela Pacheco', 'marcela.pacheco@email.com', '(11) 98765-4395', 'Análise de Sistemas'),
            ('Caio Figueiredo', 'caio.figueiredo@email.com', '(11) 98765-4396', 'Engenharia de Software'),
            ('Tatiane Araújo', 'tatiane.araujo@email.com', '(11) 98765-4397', 'Ciência da Computação'),
            ('Rodrigo Cunha', 'rodrigo.cunha@email.com', '(11) 98765-4398', 'Sistemas de Informação'),
            ('Daniela Torres', 'daniela.torres@email.com', '(11) 98765-4399', 'Engenharia da Computação'),
            ('Maurício Sales', 'mauricio.sales@email.com', '(11) 98765-4400', 'Análise de Sistemas'),
            ('Vivian Matos', 'vivian.matos@email.com', '(11) 98765-4401', 'Engenharia de Software'),
            ('Guilherme Paiva', 'guilherme.paiva@email.com', '(11) 98765-4402', 'Ciência da Computação'),
            ('Luciana Vieira', 'luciana.vieira@email.com', '(11) 98765-4403', 'Sistemas de Informação'),
            ('Rodrigo Farias', 'rodrigo.farias@email.com', '(11) 98765-4404', 'Engenharia da Computação'),
            ('Vanessa Tavares', 'vanessa.tavares@email.com', '(11) 98765-4405', 'Análise de Sistemas'),
            ('Douglas Nunes', 'douglas.nunes@email.com', '(11) 98765-4406', 'Engenharia de Software'),
            ('Carla Mendes', 'carla.mendes@email.com', '(11) 98765-4407', 'Ciência da Computação'),
            ('Jorge Peixoto', 'jorge.peixoto@email.com', '(11) 98765-4408', 'Sistemas de Informação'),
            ('Beny Basaula Kiamvu II', 'itsbenyreis@outlook.com', '(00244) 922959709', 'Sistemas de Informação'),
            ('Lorena Azevedo', 'lorena.azevedo@email.com', '(11) 98765-4409', 'Engenharia da Computação'),
            ('Fábio Santos', 'fabio.santos@email.com', '(11) 98765-4410', 'Análise de Sistemas'),
            ('Érica Lima', 'erica.lima@email.com', '(11) 98765-4411', 'Engenharia de Software'),
            ('Bruno Nascimento', 'bruno.nascimento@email.com', '(11) 98765-4412', 'Ciência da Computação'),
            ('Sofia Correia', 'sofia.correia@email.com', '(11) 98765-4413', 'Sistemas de Informação'),
            ('Matheus Rocha', 'matheus.rocha@email.com', '(11) 98765-4414', 'Engenharia da Computação'),
            ('Caroline Teixeira', 'caroline.teixeira@email.com', '(11) 98765-4415', 'Análise de Sistemas'),
            ('Rogério Lima', 'rogerio.lima@email.com', '(11) 98765-4416', 'Engenharia de Software'),
            ('Fernanda Duarte', 'fernanda.duarte@email.com', '(11) 98765-4417', 'Ciência da Computação'),
            ('Diego Almeida', 'diego.almeida@email.com', '(11) 98765-4418', 'Sistemas de Informação'),
            ('Natália Farias', 'natalia.farias@email.com', '(11) 98765-4419', 'Engenharia da Computação'),
            ('Vinícius Oliveira', 'vinicius.oliveira@email.com', '(11) 98765-4420', 'Análise de Sistemas'),
            ('Andressa Melo', 'andressa.melo@email.com', '(11) 98765-4421', 'Engenharia de Software'),
            ('Rodrigo Neves', 'rodrigo.neves@email.com', '(11) 98765-4422', 'Ciência da Computação'),
            ('Camila Barbosa', 'camila.barbosa@email.com', '(11) 98765-4423', 'Sistemas de Informação'),
            ('Igor Batista', 'igor.batista@email.com', '(11) 98765-4424', 'Engenharia da Computação'),
            ('Lívia Torres', 'livia.torres@email.com', '(11) 98765-4425', 'Análise de Sistemas'),
            ('Sérgio Pinto', 'sergio.pinto@email.com', '(11) 98765-4426', 'Engenharia de Software'),
            ('Juliana Costa', 'juliana.costa@email.com', '(11) 98765-4427', 'Ciência da Computação'),
            ('Otávio Gomes', 'otavio.gomes@email.com', '(11) 98765-4428', 'Sistemas de Informação'),
            ('Amanda Figueiredo', 'amanda.figueiredo@email.com', '(11) 98765-4429', 'Engenharia da Computação'),
            ('Ricardo Barbosa', 'ricardo.barbosa@email.com', '(11) 98765-4430', 'Análise de Sistemas'),
            ('Helena Ribeiro', 'helena.ribeiro@email.com', '(11) 98765-4431', 'Engenharia de Software'),
            ('César Albuquerque', 'cesar.albuquerque@email.com', '(11) 98765-4432', 'Ciência da Computação'),
            ('Jéssica Moura', 'jessica.moura@email.com', '(11) 98765-4433', 'Sistemas de Informação'),
            ('Felipe Azevedo', 'felipe.azevedo@email.com', '(11) 98765-4434', 'Engenharia da Computação'),
            ('Patrícia Rocha', 'patricia.rocha@email.com', '(11) 98765-4435', 'Análise de Sistemas'),
            ('Gabriel Vieira', 'gabriel.vieira@email.com', '(11) 98765-4436', 'Engenharia de Software'),
            ('Larissa Martins', 'larissa.martins@email.com', '(11) 98765-4437', 'Ciência da Computação'),
            ('Eduardo Lopes', 'eduardo.lopes@email.com', '(11) 98765-4438', 'Sistemas de Informação'),
            ('Manuela Fernandes', 'manuela.fernandes@email.com', '(11) 98765-4439', 'Engenharia da Computação'),
            ('Rafael Cardoso', 'rafael.cardoso@email.com', '(11) 98765-4440', 'Análise de Sistemas'),
            ('Luana Pires', 'luana.pires@email.com', '(11) 98765-4441', 'Engenharia de Software'),
            ('Pedro Barbosa', 'pedro.barbosa@email.com', '(11) 98765-4442', 'Ciência da Computação'),
            ('Juliana Rezende', 'juliana.rezende@email.com', '(11) 98765-4443', 'Sistemas de Informação'),
            ('Carlos Eduardo', 'carlos.eduardo@email.com', '(11) 98765-4444', 'Engenharia da Computação'),
            ('Raquel Nogueira', 'raquel.nogueira@email.com', '(11) 98765-4445', 'Análise de Sistemas'),
            ('André Tavares', 'andre.tavares@email.com', '(11) 98765-4446', 'Engenharia de Software'),
            ('Tatiana Gomes', 'tatiana.gomes@email.com', '(11) 98765-4447', 'Ciência da Computação'),
            ('Leonardo Rocha', 'leonardo.rocha@email.com', '(11) 98765-4448', 'Sistemas de Informação'),
            ('Vanessa Duarte', 'vanessa.duarte@email.com', '(11) 98765-4449', 'Engenharia da Computação'),
            ('Gustavo Barros', 'gustavo.barros@email.com', '(11) 98765-4450', 'Análise de Sistemas'),
            ('Cláudia Ribeiro', 'claudia.ribeiro@email.com', '(11) 98765-4451', 'Engenharia de Software'),
            ('Thiago Martins', 'thiago.martins@email.com', '(11) 98765-4452', 'Ciência da Computação'),
            ('Carolina Souza', 'carolina.souza@email.com', '(11) 98765-4453', 'Sistemas de Informação'),
            ('João Pedro', 'joao.pedro@email.com', '(11) 98765-4454', 'Engenharia da Computação'),
            ('Marcela Duarte', 'marcela.duarte@email.com', '(11) 98765-4455', 'Análise de Sistemas'),
            ('Eduardo Almeida', 'eduardo.almeida2@email.com', '(11) 98765-4456', 'Engenharia de Software'),
            ('Sabrina Lopes', 'sabrina.lopes@email.com', '(11) 98765-4457', 'Ciência da Computação'),
            ('Rafael Mendes', 'rafael.mendes@email.com', '(11) 98765-4458', 'Sistemas de Informação'),
            ('Bianca Oliveira', 'bianca.oliveira@email.com', '(11) 98765-4459', 'Engenharia da Computação'),
            ('Anderson Teixeira', 'anderson.teixeira@email.com', '(11) 98765-4460', 'Análise de Sistemas'),
            ('Mônica Fernandes', 'monica.fernandes@email.com', '(11) 98765-4461', 'Engenharia de Software'),
            ('Paulo Henrique', 'paulo.henrique@email.com', '(11) 98765-4462', 'Ciência da Computação'),
            ('Cristiane Matos', 'cristiane.matos@email.com', '(11) 98765-4463', 'Sistemas de Informação'),
            ('Mateus Nogueira', 'mateus.nogueira@email.com', '(11) 98765-4464', 'Engenharia da Computação'),
            ('Suelen Barros', 'suelen.barros@email.com', '(11) 98765-4465', 'Análise de Sistemas'),
            ('Renato Pires', 'renato.pires@email.com', '(11) 98765-4466', 'Engenharia de Software'),
            ('Amanda Carvalho', 'amanda.carvalho@email.com', '(11) 98765-4467', 'Ciência da Computação'),
            ('Felipe Silva', 'felipe.silva@email.com', '(11) 98765-4468', 'Sistemas de Informação'),
            ('Camila Ribeiro', 'camila.ribeiro@email.com', '(11) 98765-4469', 'Engenharia da Computação'),
            ('Luciano Moraes', 'luciano.moraes@email.com', '(11) 98765-4470', 'Análise de Sistemas'),
            ('Juliana Alves', 'juliana.alves@email.com', '(11) 98765-4471', 'Engenharia de Software'),
            ('Bruno Fernandes', 'bruno.fernandes@email.com', '(11) 98765-4472', 'Ciência da Computação'),
            ('Patrícia Mendes', 'patricia.mendes@email.com', '(11) 98765-4473', 'Sistemas de Informação'),
            ('Rodrigo Oliveira', 'rodrigo.oliveira@email.com', '(11) 98765-4474', 'Engenharia da Computação'),
            ('Camila Duarte', 'camila.duarte@email.com', '(11) 98765-4475', 'Análise de Sistemas'),
            ('Guilherme Souza', 'guilherme.souza@email.com', '(11) 98765-4476', 'Engenharia de Software'),
            ('Larissa Lima', 'larissa.lima@email.com', '(11) 98765-4477', 'Ciência da Computação'),
            ('André Barbosa', 'andre.barbosa@email.com', '(11) 98765-4478', 'Sistemas de Informação'),
            ('Fernanda Pires', 'fernanda.pires@email.com', '(11) 98765-4479', 'Engenharia da Computação'),
            ('Rafael Batista', 'rafael.batista@email.com', '(11) 98765-4480', 'Análise de Sistemas'),
            ('Isabela Ferreira', 'isabela.ferreira@email.com', '(11) 98765-4481', 'Engenharia de Software'),
            ('Marcelo Gomes', 'marcelo.gomes@email.com', '(11) 98765-4482', 'Ciência da Computação'),
            ('Priscila Rocha', 'priscila.rocha@email.com', '(11) 98765-4483', 'Sistemas de Informação'),
            ('José Carlos', 'jose.carlos@email.com', '(11) 98765-4484', 'Engenharia da Computação'),
            ('Débora Lima', 'debora.lima@email.com', '(11) 98765-4485', 'Análise de Sistemas'),
            ('Tiago Ribeiro', 'tiago.ribeiro@email.com', '(11) 98765-4486', 'Engenharia de Software'),
            ('Cristina Duarte', 'cristina.duarte@email.com', '(11) 98765-4487', 'Ciência da Computação'),
            ('Alexandre Silva', 'alexandre.silva@email.com', '(11) 98765-4488', 'Sistemas de Informação'),
            ('Tatiane Moreira', 'tatiane.moreira@email.com', '(11) 98765-4489', 'Engenharia da Computação'),
            ('Paula Almeida', 'paula.almeida@email.com', '(11) 98765-4490', 'Análise de Sistemas'),
            ('Lucas Henrique', 'lucas.henrique@email.com', '(11) 98765-4491', 'Engenharia de Software'),
            ('Simone Freitas', 'simone.freitas@email.com', '(11) 98765-4492', 'Ciência da Computação'),
            ('Caio Santos', 'caio.santos@email.com', '(11) 98765-4493', 'Sistemas de Informação'),
            ('Marta Ferreira', 'marta.ferreira@email.com', '(11) 98765-4494', 'Engenharia da Computação'),
            ('João Paulo', 'joao.paulo@email.com', '(11) 98765-4495', 'Análise de Sistemas'),
            ('Camila Martins', 'camila.martins@email.com', '(11) 98765-4496', 'Engenharia de Software'),
            ('Anderson Silva', 'anderson.silva@email.com', '(11) 98765-4497', 'Ciência da Computação'),
            ('Letícia Souza', 'leticia.souza@email.com', '(11) 98765-4498', 'Sistemas de Informação'),
            ('Eduardo Costa', 'eduardo.costa@email.com', '(11) 98765-4499', 'Engenharia da Computação'),
            ('Gabriela Lima', 'gabriela.lima@email.com', '(11) 98765-4500', 'Análise de Sistemas')
        ]
        conn.executemany('INSERT INTO alunos (nome, email, telefone, curso) VALUES (?, ?, ?, ?)', estudantes)
        conn.commit()
        print(f"{count} estudantes foram adicionados ao banco de dados!")
    else:
        print(f"O banco já contém {count} registros. Nenhum dado foi inserido.")
    
    conn.close()


init_db()
popular_banco_dados()


if __name__ == '__main__':
    app.run(debug=True)
