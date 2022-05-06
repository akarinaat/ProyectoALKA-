from cmath import nan
from ssl import ALERT_DESCRIPTION_CERTIFICATE_UNOBTAINABLE
from typing import List
from alkaparser import ALKA_parser
from lark import Token, Tree, tree
from dataclasses import dataclass
from enum import Enum


class SemanticError(Exception):
    pass


class Tipo(Enum):
    Float = "float"
    Int = "int"
    String = "string"
    Bool = "bool"


@dataclass  # son para guardar información
class Variable:

    tipo: str
    nombre: str
    dimensiones: int


@dataclass
class Funcion:

    tipo: str
    nombre: str


class AnalizadorSemantico:

    def __init__(self, input) -> None:
        # Directorio de variables, en lista para poder analizar las globales y las locales
        self.directoriosVariables = [{}]
        self.directorioFunciones = {}  # Directorio de funciones
        self.arbol: Tree = ALKA_parser.parse(input)

    def analizarArbol(self):
        for subtree in self.arbol.children:
            # print(subtree)
            if subtree.data == "decvars":
                self.analizar_decvars(subtree)
            elif subtree.data == "decfuncs":
                self.analizar_decfuncs(subtree)

    def analizar_decvars(self, subtree: Tree) -> None:
        for decvar in subtree.children:
            self.analizar_decvar(decvar)

    def analizar_decfuncs(self, subtree: Tree) -> None:
        for decfunc in subtree.children:
            self.analizar_decfunc(decfunc)

    def analizar_decvar(self, subtree: Tree) -> None:
        tipo = subtree.children[0].children[0]
        variables = subtree.children[1:]

        for variable in variables:
            nombre = variable.children[0].children[0]
            # Encontrar con cuantas dimensiones tiene la variable
            len_dimensiones = len(variable.children[1:])
            self.declarar_variable(nombre, tipo, len_dimensiones)
            # print(variable.pretty())

    def declarar_variable(self, nombre, tipo: str, dimensiones: int):
        # checar si ya existe la variable en la lista de directorios
        for directorio in self.directoriosVariables:
            if nombre in directorio:
                raise SemanticError("ID ya existe")
        # Si no existe declararlo en el último directorio (-1)
        self.directoriosVariables[-1][str(nombre)
                                      ] = Variable(Tipo(tipo), str(nombre), dimensiones)

    def analizar_decfunc(self, subtree: Tree) -> None:

        self.directoriosVariables.append({})
        tipo = subtree.children[0].children[0]
        nombre = subtree.children[1].children[0]
        if nombre in self.directorioFunciones:
            raise SemanticError("funcion ya existe")
        else:
            self.directorioFunciones[nombre] = Funcion(Tipo(tipo), nombre)
        # declarar los argumentos
        # print(subtree.children[2:-2], len(subtree.children[2:-2]))
        for argumento in chunker(subtree.children[2:-2], 2):
            nombre_argumento = argumento[0].children[0]
            tipo_argumento = argumento[1].children[0]
            self.declarar_variable(nombre_argumento, Tipo(tipo_argumento), 0)

        decvars = subtree.children[-2]
        estatutos = subtree.children[-1].children

        for decvar in decvars.children:
            self.analizar_decvar(decvar)

        # analizar el cuerpo de la función
        self.analizar_estatutos(estatutos)

    def analizar_estatutos(self, estatutos: List[Tree]) -> None:
        for estatuto in estatutos:
            self.analizar_estatuto(estatuto)

    def analizar_estatuto(self, estatuto: Tree) -> None:
        # (asignacion | llamadafuncion | expresion | if | while | forloop | return) ";"
        # El unico que regresa un valor es el returns
        if estatuto.children[0].data == "expresion":
            self.analizar_expresion(estatuto.children[0])
        elif estatuto.children[0].data == "asignacion":
            self.analizar_asignacion(estatuto.children[0])
        elif estatuto.children[0].data == "llamadafuncion":
            pass
        elif estatuto.children[0].data == "if":
            self.analizar_if(estatuto.children[0])
        elif estatuto.children[0].data == "return":
            self.analizar_return(estatuto.children[0])
            
        elif estatuto.children[0].data == "forloop":
            pass
        elif estatuto.children[0].data == "while":
            self.analizar_while(estatuto.children[0])
            pass

    def analizar_asignacion(self, arbol_asignacion: Tree) -> None:
        # llamadavariable "=" expresion
        arbol_llamada_variable = arbol_asignacion.children[0]
        arbol_expresion = arbol_asignacion.children[1]

        tipo_llamada_variable = self.analizar_llamadavariable(
            arbol_llamada_variable)
        tipo_expresion = self.analizar_expresion(arbol_expresion)

        # Comparar los tipos
        if tipo_llamada_variable != tipo_expresion:
            raise SemanticError("Tipos incompatibles")


# regresa booleano si es > o < else el tipo de la exp


    def analizar_expresion(self, expresion: Tree) -> Tipo:
        print(expresion.pretty())
        if len(expresion.children) == 1:
            exp = expresion.children[0]
            return self.analizar_exp(exp)
            # si es una comoparación
        elif len(expresion.children) == 3:
            exp1 = expresion.children[0]
            exp2 = expresion.children[2]
            tipo_exp1 = self.analizar_exp(exp1)
            tipo_exp2 = self.analizar_exp(exp2)

            if tipo_exp1 == tipo_exp2:
                return Tipo.Bool
                # return Tipo("bool")
            else:
                raise SemanticError("No se pueden comparar")

        else:
            raise SemanticError("Expresion mal formada")

    def analizar_exp(self, exp: Tree):
        return self.analizar_operacion_binaria(exp, self.analizar_termino)

    def analizar_termino(self, termino: Tree):
        return self.analizar_operacion_binaria(termino, self.analizar_factor)

    def analizar_factor(self, factor: Tree):
        if len(factor.children) == 1:
            expresion = factor.children[0]
            if expresion.data == "expresion":
                return self.analizar_expresion(expresion)
            else:
                return self.analizar_atomo(expresion)
        elif len(factor.children) == 2:
            atomo = factor.children[1]
            return self.analizar_atomo(atomo)

        else:
            raise SemanticError("Factor mal formado")

    def analizar_atomo(self, atomo: Tree) -> Tipo:
        atomo = atomo.children[0]
        if isinstance(atomo, Token):
            print(atomo.type)
            if atomo.type == "CTEI":
                return Tipo.Int
            elif atomo.type == "CTEF":
                return Tipo.Float
            elif atomo.type == "CTESTR":
                return Tipo.String
        else:
            if atomo.data == "llamadavariable":
               # print(atomo.pretty())
                return self.analizar_llamadavariable(atomo)
                # que efectivamente si tenga las 2 dimensiones

            if atomo.data == "llamadafuncion":
                # Checar que la función esté declarada
                # Que tiene la cantidad correcta de argumentos
                # Checar que los argumentos tengan el tipo correcto
                pass
            if atomo.data == "funcionesespeciales":
                # Checar que se llame con el tipo correcto
                pass

    def analizar_llamadavariable(self, arbol_llamada_variable: Tree):
        nombre_variable = str(arbol_llamada_variable.children[0].children[0])
        # Checar que esté declarada
        variable = None
        for directorio in self.directoriosVariables:
            if nombre_variable in directorio:
                variable = directorio[nombre_variable]
                break
        if variable is None:
            raise SemanticError("Error, la variable no esta declarada")
        # Checar que se llame con la cantidad de dimensiones correcta (por ejemplo si es una matriz de dos dimensiones)
        len_dimensiones = len(arbol_llamada_variable.children[1:])
        if len_dimensiones != variable.dimensiones:
            raise SemanticError("Dimensiones incorrectas")
        else:
            # Tengo que confirmar que son del mismo tipo, ejemplo 2+2 = int+int
            # Es lo último que se verifica (en la gramática)
            return variable.tipo

    def analizar_operacion_binaria(self, operacion: Tree, funcion):
        lista_operandos = operacion.children[::2]
        tipo = funcion(lista_operandos[0])
        # para que no se cheque el primero dos veces
        for operando in lista_operandos[1:]:
            if funcion(operando) != tipo:
                raise SemanticError("Tipos incompatibles")

        return tipo

    # if : "if" "(" expresion ")" "{" estatutos "}" else
    def analizar_if(self, arbol_if: Tree):
        arbol_expresion = arbol_if.children[0]
        arbol_estatutos = arbol_if.children[1]
        arbol_else = arbol_if.children[2]

        tipo_arbol_expresion = self.analizar_expresion(arbol_expresion)
        if tipo_arbol_expresion != Tipo.Bool:
            raise SemanticError("Tipo no booleano")

        self.analizar_estatutos(arbol_estatutos)
        self.analizar_else(arbol_else)

    def analizar_else(self, arbol_else: Tree) -> None:
        if len(arbol_else.children) != 0:
           self.analizar_estatutos(arbol_else.children[0]) 
        
    def analizar_return(self, arbol_return:Tree)->Tipo:
        expresion = arbol_return.children[0]
        #Regresa un tipo
        return self.analizar_expresion(expresion) 

    # while : "while" "(" expresion ")" "{" estatutos "}"
    def analizar_while(self, arbol_while:Tree):
        arbol_expresion_while = arbol_while.children[0]
        arbol_estatutos_while = arbol_while.children[1]

        tipo_expresion_while = self.analizar_expresion(arbol_expresion_while)
        self.analizar_estatutos(arbol_estatutos_while)

        if tipo_expresion_while != Tipo.Bool:
            raise SemanticError("Tipo no booleano")


def get_token(subtree: Tree, token_type: str):
    return [token.value for token in filter(lambda t: t.type == token_type,
                                            subtree.scan_values(
                                                lambda v: isinstance(v, Token))  # Los tokens del subtree
                                            )]


def chunker(seq, size):
    return (seq[pos: pos + size] for pos in range(0, len(seq), size))
