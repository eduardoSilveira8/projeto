from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
import mysql.connector

app = FastAPI(title="EconoApp API")

# =========================
# CONFIG BANCO DE DADOS
# =========================

DB_CONFIG = {
    "host": "sql10.freesqldatabase.com",
    "user": "sql10809393",
    "password": "2IF2GFWYvv",
    "database": "sql10809393",
    "port": 3306
}


def get_db():
    conn = mysql.connector.connect(**DB_CONFIG)
    try:
        yield conn
    finally:
        conn.close()


# =========================
# MODELOS Pydantic
# =========================

# ----- USUÁRIOS -----
class UsuarioCreate(BaseModel):
    nome: str
    email: EmailStr
    senha_hash: str  # aqui você pode enviar a senha já hasheada


class UsuarioUpdate(BaseModel):
    nome: Optional[str] = None
    email: Optional[EmailStr] = None
    senha_hash: Optional[str] = None


# ----- CATEGORIAS -----
class CategoriaCreate(BaseModel):
    nome: str
    tipo: str  # 'R' ou 'D', etc.


class CategoriaUpdate(BaseModel):
    nome: Optional[str] = None
    tipo: Optional[str] = None


# ----- FINANÇAS -----
class FinancaCreate(BaseModel):
    id_usuario: int
    tipo: str           # 'R' ou 'D', etc.
    id_categoria: Optional[int] = None
    descricao: Optional[str] = None
    valor: float
    data: datetime      # enviar em ISO: "2025-11-25T10:00:00"


class FinancaUpdate(BaseModel):
    id_usuario: Optional[int] = None
    tipo: Optional[str] = None
    id_categoria: Optional[int] = None
    descricao: Optional[str] = None
    valor: Optional[float] = None
    data: Optional[datetime] = None


# ----- TAGS -----
class TagCreate(BaseModel):
    nome: str
    cor: str           # ex: "FF0000"
    id_usuario: Optional[int] = None


class TagUpdate(BaseModel):
    nome: Optional[str] = None
    cor: Optional[str] = None
    id_usuario: Optional[int] = None


# ----- FINANCAS_TAGS -----
class FinancaTagCreate(BaseModel):
    id_financa: int
    id_tag: int


# =========================
# UTIL
# =========================

def row_or_404(cursor, msg="Registro não encontrado"):
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=msg)
    return row


# =========================
# CRUD USUÁRIOS
# =========================

@app.get("/usuarios")
def listar_usuarios(db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM usuarios ORDER BY id")
    return cursor.fetchall()


@app.get("/usuarios/{usuario_id}")
def obter_usuario(usuario_id: int, db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM usuarios WHERE id = %s", (usuario_id,))
    return row_or_404(cursor, "Usuário não encontrado")


@app.post("/usuarios", status_code=201)
def criar_usuario(dados: UsuarioCreate, db=Depends(get_db)):
    cursor = db.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO usuarios (nome, email, senha_hash)
            VALUES (%s, %s, %s)
            """,
            (dados.nome, dados.email, dados.senha_hash)
        )
        db.commit()
        new_id = cursor.lastrowid
    except mysql.connector.IntegrityError as e:
        # email único
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cursor.close()

    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM usuarios WHERE id = %s", (new_id,))
    return cursor.fetchone()


@app.put("/usuarios/{usuario_id}")
def atualizar_usuario(usuario_id: int, dados: UsuarioUpdate, db=Depends(get_db)):
    campos = []
    valores = []

    if dados.nome is not None:
        campos.append("nome = %s")
        valores.append(dados.nome)
    if dados.email is not None:
        campos.append("email = %s")
        valores.append(dados.email)
    if dados.senha_hash is not None:
        campos.append("senha_hash = %s")
        valores.append(dados.senha_hash)

    if not campos:
        raise HTTPException(status_code=400, detail="Nada para atualizar.")

    valores.append(usuario_id)

    cursor = db.cursor()
    cursor.execute("SELECT 1 FROM usuarios WHERE id = %s", (usuario_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    try:
        cursor.execute(
            f"UPDATE usuarios SET {', '.join(campos)} WHERE id = %s",
            valores
        )
        db.commit()
    finally:
        cursor.close()

    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM usuarios WHERE id = %s", (usuario_id,))
    return cursor.fetchone()


@app.delete("/usuarios/{usuario_id}", status_code=204)
def deletar_usuario(usuario_id: int, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("DELETE FROM usuarios WHERE id = %s", (usuario_id,))
    db.commit()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return


# =========================
# CRUD CATEGORIAS
# =========================

@app.get("/categorias")
def listar_categorias(db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM categorias ORDER BY id")
    return cursor.fetchall()


@app.get("/categorias/{categoria_id}")
def obter_categoria(categoria_id: int, db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM categorias WHERE id = %s", (categoria_id,))
    return row_or_404(cursor, "Categoria não encontrada")


@app.post("/categorias", status_code=201)
def criar_categoria(dados: CategoriaCreate, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO categorias (nome, tipo) VALUES (%s, %s)",
        (dados.nome, dados.tipo)
    )
    db.commit()
    new_id = cursor.lastrowid
    cursor.close()

    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM categorias WHERE id = %s", (new_id,))
    return cursor.fetchone()


@app.put("/categorias/{categoria_id}")
def atualizar_categoria(categoria_id: int, dados: CategoriaUpdate, db=Depends(get_db)):
    campos = []
    valores = []

    if dados.nome is not None:
        campos.append("nome = %s")
        valores.append(dados.nome)
    if dados.tipo is not None:
        campos.append("tipo = %s")
        valores.append(dados.tipo)

    if not campos:
        raise HTTPException(status_code=400, detail="Nada para atualizar.")

    valores.append(categoria_id)

    cursor = db.cursor()
    cursor.execute("SELECT 1 FROM categorias WHERE id = %s", (categoria_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Categoria não encontrada")

    cursor.execute(
        f"UPDATE categorias SET {', '.join(campos)} WHERE id = %s",
        valores
    )
    db.commit()
    cursor.close()

    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM categorias WHERE id = %s", (categoria_id,))
    return cursor.fetchone()


@app.delete("/categorias/{categoria_id}", status_code=204)
def deletar_categoria(categoria_id: int, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("DELETE FROM categorias WHERE id = %s", (categoria_id,))
    db.commit()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    return


# =========================
# CRUD FINANÇAS
# =========================

@app.get("/financas")
def listar_financas(db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM financas ORDER BY data DESC, id DESC")
    return cursor.fetchall()


@app.get("/financas/{financa_id}")
def obter_financa(financa_id: int, db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM financas WHERE id = %s", (financa_id,))
    return row_or_404(cursor, "Finança não encontrada")


@app.post("/financas", status_code=201)
def criar_financa(dados: FinancaCreate, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute(
        """
        INSERT INTO financas (id_usuario, tipo, id_categoria, descricao, valor, data)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (dados.id_usuario, dados.tipo, dados.id_categoria,
         dados.descricao, dados.valor, dados.data)
    )
    db.commit()
    new_id = cursor.lastrowid
    cursor.close()

    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM financas WHERE id = %s", (new_id,))
    return cursor.fetchone()


@app.put("/financas/{financa_id}")
def atualizar_financa(financa_id: int, dados: FinancaUpdate, db=Depends(get_db)):
    campos = []
    valores = []

    if dados.id_usuario is not None:
        campos.append("id_usuario = %s")
        valores.append(dados.id_usuario)
    if dados.tipo is not None:
        campos.append("tipo = %s")
        valores.append(dados.tipo)
    if dados.id_categoria is not None:
        campos.append("id_categoria = %s")
        valores.append(dados.id_categoria)
    if dados.descricao is not None:
        campos.append("descricao = %s")
        valores.append(dados.descricao)
    if dados.valor is not None:
        campos.append("valor = %s")
        valores.append(dados.valor)
    if dados.data is not None:
        campos.append("data = %s")
        valores.append(dados.data)

    if not campos:
        raise HTTPException(status_code=400, detail="Nada para atualizar.")

    valores.append(financa_id)

    cursor = db.cursor()
    cursor.execute("SELECT 1 FROM financas WHERE id = %s", (financa_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Finança não encontrada")

    cursor.execute(
        f"UPDATE financas SET {', '.join(campos)} WHERE id = %s",
        valores
    )
    db.commit()
    cursor.close()

    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM financas WHERE id = %s", (financa_id,))
    return cursor.fetchone()


@app.delete("/financas/{financa_id}", status_code=204)
def deletar_financa(financa_id: int, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("DELETE FROM financas WHERE id = %s", (financa_id,))
    db.commit()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Finança não encontrada")
    return


# =========================
# CRUD TAGS
# =========================

@app.get("/tags")
def listar_tags(db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM tags ORDER BY id")
    return cursor.fetchall()


@app.get("/tags/{tag_id}")
def obter_tag(tag_id: int, db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM tags WHERE id = %s", (tag_id,))
    return row_or_404(cursor, "Tag não encontrada")


@app.post("/tags", status_code=201)
def criar_tag(dados: TagCreate, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute(
        """
        INSERT INTO tags (nome, cor, id_usuario)
        VALUES (%s, %s, %s)
        """,
        (dados.nome, dados.cor, dados.id_usuario)
    )
    db.commit()
    new_id = cursor.lastrowid
    cursor.close()

    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM tags WHERE id = %s", (new_id,))
    return cursor.fetchone()


@app.put("/tags/{tag_id}")
def atualizar_tag(tag_id: int, dados: TagUpdate, db=Depends(get_db)):
    campos = []
    valores = []

    if dados.nome is not None:
        campos.append("nome = %s")
        valores.append(dados.nome)
    if dados.cor is not None:
        campos.append("cor = %s")
        valores.append(dados.cor)
    if dados.id_usuario is not None:
        campos.append("id_usuario = %s")
        valores.append(dados.id_usuario)

    if not campos:
        raise HTTPException(status_code=400, detail="Nada para atualizar.")

    valores.append(tag_id)

    cursor = db.cursor()
    cursor.execute("SELECT 1 FROM tags WHERE id = %s", (tag_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Tag não encontrada")

    cursor.execute(
        f"UPDATE tags SET {', '.join(campos)} WHERE id = %s",
        valores
    )
    db.commit()
    cursor.close()

    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM tags WHERE id = %s", (tag_id,))
    return cursor.fetchone()


@app.delete("/tags/{tag_id}", status_code=204)
def deletar_tag(tag_id: int, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("DELETE FROM tags WHERE id = %s", (tag_id,))
    db.commit()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Tag não encontrada")
    return


# =========================
# CRUD FINANCAS_TAGS
# =========================

@app.get("/financas-tags")
def listar_financas_tags(db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM financas_tags ORDER BY id_financa, id_tag")
    return cursor.fetchall()


@app.post("/financas-tags", status_code=201)
def criar_financa_tag(dados: FinancaTagCreate, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute(
        """
        INSERT INTO financas_tags (id_financa, id_tag)
        VALUES (%s, %s)
        """,
        (dados.id_financa, dados.id_tag)
    )
    db.commit()
    cursor.close()
    return {"message": "Vínculo criado com sucesso"}


@app.delete("/financas-tags/{id_financa}/{id_tag}", status_code=204)
def deletar_financa_tag(id_financa: int, id_tag: int, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute(
        "DELETE FROM financas_tags WHERE id_financa = %s AND id_tag = %s",
        (id_financa, id_tag)
    )
    db.commit()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Vínculo não encontrado")
    return


