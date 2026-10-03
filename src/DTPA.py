########################################################
#######   DTPA - DISEÑADOR DE TORNEOS PRAELIUM AUSTRALIS
########################################################

### VERSION 0.1

### PROTOTIPO ORIENTADO AL TORNEO DE NOVATOS DE HEMA CHILE 2026

##########################################################
## COMENTARIOS E INDICACIONES PREVIAS
##########################################################

## Debido a los conflictos de compatbilidad entre ete3 y las versiones más recientes de python, se recomienda proceder de la siguiente forma
## Crear un ambiente de conda|anaconda especificando la versión de python 3.11
## conda create --name NNOMBRE python=3.11
## Instalar lo paquetes requeridos en el código; por ejemplo: pandas
## Para instalar ete3, no utilizar etetoolkit; en cambio, usar el canal conda forge
## conda install -c conda-forge ete3

## para el funcionamiento correcto del styler que muestra lso grupos y demás en html, usar:
## conda install -c conda-forge jinja2

#########################################################
## PAQUETES NECESARIOS
#########################################################

import pandas as pd
import random as rd
import ete3 as et
import itertools

from tkinter import *
from tkinter import ttk, filedialog, messagebox
from PIL import ImageTk, Image
import os
import sys
import pickle
import ctypes
import subprocess

##############################################################
### "magia" para que la pantalla de mierda no se vea borrosa
#############################################################


if sys.platform.startswith("win"):
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDpiAwarenessContext(-4)
        except Exception:
            pass

########################################################
## DEFINICIÓN DE CLASES Y FUNCIONES PRINCIPALES
########################################################

class Esgrimista:
    def __init__(self, nombre: str, club: str):
        self.nombre = nombre
        self.club = club
        self.puntaje = []
        
        self.faltas_graves_totales = 0
        self.descalificado = False
        
        self.faltas_leves_totales = 0
        self.derrotas_por_faltas = 0
        self.historial_sanciones = []

    @property
    def puntos_totales(self) -> int:
        return sum(duelo[0] for duelo in self.puntaje)

    @property
    def diferencia_total(self) -> int:
        return sum(duelo[1] for duelo in self.puntaje)

    def registrar_falta_grave(self, fase="Grupos", duelo_str="Ninguno"):
        if not self.descalificado:
            self.faltas_graves_totales += 1
            self.historial_sanciones.append({"fase": fase, "duelo": duelo_str, "tipo": "Grave"})
            if self.faltas_graves_totales >= 2:
                self.descalificado = True

    def __repr__(self):
        estado_desc = " [DESCALIFICADO]" if self.descalificado else ""
        return f"{self.nombre} ({self.club}) | Pts: {self.puntos_totales}, Dif: {self.diferencia_total}{estado_desc}"


class Duelo:
    def __init__(self, esgrimista_a: Esgrimista, esgrimista_b: Esgrimista):
        self.esgrimista_a = esgrimista_a
        self.esgrimista_b = esgrimista_b
        self.resuelto = False
        self.faltas_leves_a = 0
        self.faltas_leves_b = 0
        
        self.puntaje_a_ingresado = "-"
        self.puntaje_b_ingresado = "-"

    def registrar_falta_leve_a(self, fase="Grupos"):
        self.faltas_leves_a += 1
        self.esgrimista_a.faltas_leves_totales += 1
        duelo_str = f"{self.esgrimista_a.nombre} vs {self.esgrimista_b.nombre}"
        self.esgrimista_a.historial_sanciones.append({"fase": fase, "duelo": duelo_str, "tipo": "Leve"})
        
        if self.faltas_leves_a >= 3:
            self.esgrimista_a.derrotas_por_faltas += 1
            self.asignar_resultado(0, self.puntaje_b_ingresado)

    def registrar_falta_leve_b(self, fase="Grupos"):
        self.faltas_leves_b += 1
        self.esgrimista_b.faltas_leves_totales += 1
        duelo_str = f"{self.esgrimista_a.nombre} vs {self.esgrimista_b.nombre}"
        self.esgrimista_b.historial_sanciones.append({"fase": fase, "duelo": duelo_str, "tipo": "Leve"})
        
        if self.faltas_leves_b >= 3:
            self.esgrimista_b.derrotas_por_faltas += 1
            self.asignar_resultado(self.puntaje_a_ingresado, 0)

    def asignar_resultado(self, puntos_a: int, puntos_b: int):
        if self.resuelto:
            self.esgrimista_a.puntaje.pop()
            self.esgrimista_b.puntaje.pop()
            
        self.puntaje_a_ingresado = puntos_a
        self.puntaje_b_ingresado = puntos_b
        
        diferencia_a = puntos_a - puntos_b
        diferencia_b = puntos_b - puntos_a

        if puntos_a > puntos_b:
            pts_asignado_a, pts_asignado_b = 3,0
        elif puntos_b > puntos_a:
            pts_asignado_a, pts_asignado_b = 0,3
        else:
            pts_asignado_a, pts_asignado_b = 1,1
            
        self.esgrimista_a.puntaje.append([pts_asignado_a, diferencia_a])
        self.esgrimista_b.puntaje.append([pts_asignado_b, diferencia_b])
        self.resuelto = True


class Grupo:
    def __init__(self, numero : int, capacidad: int):
        if capacidad not in [3,4,5]:
            raise ValueError("La capacidad del grupo puede ser únicamente 3, 4 o 5")

        self.numero  = numero
        self.capacidad = capacidad
        self.integrantes = []
        self.duelos = []

    def verificar_espacios(self) -> bool:
        return len(self.integrantes) < self.capacidad

    def verificar_club(self, club: str) -> bool:
        return any(e.club == club for e in self.integrantes)

    def conteo_coincidencias(self) -> int:
        clubs = [e.club for e in self.integrantes]
        return len(clubs) - len(set(clubs))

    def agregar_esgrimista(self, esgrimista: Esgrimista):
        if not self.verificar_espacios():
            raise RuntimeError("El grupo ya está lleno")
        self.integrantes.append(esgrimista)

    def generar_duelos(self):
        if len(self.integrantes) < 2:
            raise ValueError("El grupo no tiene suficientes esgrimistas para generar duelos")
        parejas = itertools.combinations(self.integrantes, 2)
        self.duelos = [Duelo(a, b) for a , b in parejas]

    def posiciones(self):
        return sorted(
            self.integrantes,
            key= lambda e: (e.puntos_totales, e.diferencia_total),
            reverse = True
        )

    def clasificados(self, cantidad : int) -> list:
        return self.posiciones()[:cantidad]

    def __repr__(self):
        return f"Grupo {self.numero} (Capacidad {self.capacidad}, Integrantes: {len(self.integrantes)})"


class Categoria:
    def __init__(self, nombre: str):
        self.nombre = nombre
        self.esgrimistas = []
        self.grupos = []
        self.cupos_fijos = 0
        self.usar_terceros = False
        self.cupos_terceros = 0

    def cargar_esgrimistas(self, df_categoria : pd.DataFrame):
        for _, row in df_categoria.iterrows():
            self.esgrimistas.append(Esgrimista(row['Nombre'], row['Club']))

    def configurar_grupos(self, capacidades: list[int]):
        if sum(capacidades) != len(self.esgrimistas):
            raise ValueError(f"Error en {self.nombre}: Cupos no coinciden.")
        self.grupos = [Grupo(numero=i+1, capacidad=cap) for i, cap in enumerate(capacidades)]

    def generar_grupos(self):
        if not self.grupos:
            raise RuntimeError("Primero se debe llamar 'configurar_grupos()'")
        conteo_clubes = {}
        for e in self.esgrimistas:
            conteo_clubes[e.club] = conteo_clubes.get(e.club, 0) + 1
        esgrimistas_ordenados = sorted(
            self.esgrimistas, key=lambda e: (conteo_clubes[e.club], rd.random()), reverse=True
        )
        for esgrimista in esgrimistas_ordenados:
            candidatos = [g for g in self.grupos if g.verificar_espacios()]
            sin_conflicto = [g for g in candidatos if not g.verificar_club(esgrimista.club)]
            if sin_conflicto:
                grupo_elegido = min(sin_conflicto, key=lambda g: len(g.integrantes))
            else:
                grupo_elegido = min(candidatos, key=lambda g: (g.conteo_coincidencias(), len(g.integrantes)))
            grupo_elegido.agregar_esgrimista(esgrimista)

    def obtener_clasificados(self):
        clasificados = set()
        candidatos_terceros = []

        for g in self.grupos:
            pos = g.posiciones()
            for i in range(min(self.cupos_fijos, len(pos))):
                clasificados.add(pos[i])
            
            if self.usar_terceros and len(pos) > self.cupos_fijos:
                candidatos_terceros.append(pos[self.cupos_fijos])

        if self.usar_terceros:
            candidatos_terceros.sort(key=lambda e: (e.puntos_totales, e.diferencia_total), reverse=True)
            for i in range(min(self.cupos_terceros, len(candidatos_terceros))):
                clasificados.add(candidatos_terceros[i])

        return clasificados

    def generar_html_distribucion(self) -> str:
        html_grupos = ""
        for g in self.grupos:
            filas = []
            for e in g.integrantes:
                filas.append({
                    "Esgrimista": e.nombre,
                    "Club": e.club
                })
            
            df_grupo = pd.DataFrame(filas)
            
            styler = df_grupo.style.hide(axis='index') \
                .set_caption(f"Grupo {g.numero}") \
                .set_table_styles([
                    {'selector': 'caption', 'props': [('color', '#1a252f'), ('font-size', '18px'), ('font-weight', 'bold'), ('padding', '8px')]},
                    {'selector': 'th', 'props': [('background-color', '#940101'), ('color', 'white'), ('font-weight', 'bold'), ('text-align', 'center')]},
                    {'selector': 'td', 'props': [('text-align', 'center'), ('padding', '8px'), ('border-bottom', '1px solid #ddd')]}
                ]) \
                .set_properties(subset=['Esgrimista', 'Club'], **{'text-align': 'left'})
            
            html_grupos += f"<div class='tarjeta-grupo'>\n{styler.to_html()}\n</div>\n"

        html_final = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Distribución - {self.nombre}</title>
            <style> 
                body {{ font-family: Georgia, serif; background-color: #f4f6f7; margin: 20px; }}
                h1 {{ color: #2c3e50; text-align: center; text-transform: uppercase; margin-bottom: 30px; }}
                .contenedor-tablas {{ 
                    display: flex; 
                    flex-wrap: wrap; 
                    gap: 30px; 
                    justify-content: center; 
                    align-items: flex-start;
                }}
                .tarjeta-grupo {{
                    background-color: white;
                    padding: 15px;
                    border-radius: 8px;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                }}
            </style>
        </head>
        <body>
            <h1>Torneo de Novatos 2026<br><span style="color: #9b0000; font-size: 24px;">Distribución de Grupos - {self.nombre}</span></h1>
            <div class="contenedor-tablas">
                {html_grupos}
            </div>
        </body>
        </html>
        """
        return html_final

    def generar_html_posiciones_vivo(self) -> str:
        clasificados_set = self.obtener_clasificados()
        
        def resaltar_clasificados(row):
            es_clasificado = any(row['Esgrimista'] == c.nombre for c in clasificados_set)
            color = 'background-color: #d4efdf' if es_clasificado else ''
            return [color] * len(row)

        html_grupos = ""
        for g in self.grupos:
            clasificacion = g.posiciones()
            filas = []
            for i, e in enumerate(clasificacion):
                filas.append({
                    "Posición": i + 1, "Esgrimista": e.nombre, "Club": e.club,
                    "Puntos": e.puntos_totales, "Dif.": e.diferencia_total
                })
            
            df_grupo = pd.DataFrame(filas)
            
            styler = df_grupo.style.hide(axis='index') \
                .apply(resaltar_clasificados, axis=1) \
                .set_caption(f"Grupo {g.numero}") \
                .set_table_styles([
                    {'selector': 'caption', 'props': [('color', '#1a252f'), ('font-size', '18px'), ('font-weight', 'bold'), ('padding', '8px')]},
                    {'selector': 'th', 'props': [('background-color', "#940101"), ('color', 'white'), ('font-weight', 'bold'), ('text-align', 'center')]},
                    {'selector': 'td', 'props': [('text-align', 'center'), ('padding', '8px'), ('border-bottom', '1px solid #ddd')]}
                ]) \
                .set_properties(subset=['Esgrimista', 'Club'], **{'text-align': 'left'})
            
            html_grupos += f"<div class='tarjeta-grupo'>\n{styler.to_html()}\n</div>\n"

        html_final = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta http-equiv="refresh" content="10">
            <title>Posiciones en Vivo - {self.nombre}</title>
            <style> 
                body {{ font-family: Georgia, serif; background-color: #f4f6f7; margin: 20px; }}
                h1 {{ color: #2c3e50; text-align: center; text-transform: uppercase; margin-bottom: 30px; }}
                .contenedor-tablas {{ display: flex; flex-wrap: wrap; gap: 30px; justify-content: center; align-items: flex-start; }}
                .tarjeta-grupo {{ background-color: white; padding: 15px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
            </style>
        </head>
        <body>
            <h1>Torneo de Novatos 2026<br><span style="color: #940101; font-size: 24px;">Posiciones - {self.nombre}</span></h1>
            <div class="contenedor-tablas">\n{html_grupos}\n</div>
        </body>
        </html>
        """
        return html_final

    def generar_html_fixture_vivo(self) -> str:
        import math
        clasificados_set = self.obtener_clasificados()
        n_clasificados = len(clasificados_set)

        if n_clasificados < 2:
            return "<h2 style='font-family: Georgia; color: #940101; text-align: center;'>No hay suficientes clasificados para armar el fixture.</h2>"
        clasificados_ordenados = sorted(list(clasificados_set), key=lambda e: (e.puntos_totales, e.diferencia_total), reverse=True)
        n_rondas = math.ceil(math.log2(n_clasificados))
        n_slots = 2 ** n_rondas

        nombres_jugadores = [e.nombre for e in clasificados_ordenados]
        while len(nombres_jugadores) < n_slots:
            nombres_jugadores.append("BYE (Pasa Libre)")
        def generar_orden_bracket(n):
            if n == 1: return [1]
            mitad = generar_orden_bracket(n // 2)
            nueva = []
            for semilla in mitad:
                nueva.append(semilla)
                nueva.append(n + 1 - semilla)
            return nueva

        orden_semillas = generar_orden_bracket(n_slots)
        nombres_ordenados = [nombres_jugadores[i - 1] for i in orden_semillas]
        html_rondas = ""
        for ronda in range(n_rondas, 0, -1):
            if ronda == 1: nombre_fase = "FINAL"
            elif ronda == 2: nombre_fase = "SEMIFINAL"
            elif ronda == 3: nombre_fase = "CUARTOS DE FINAL"
            elif ronda == 4: nombre_fase = "OCTAVOS DE FINAL"
            else: nombre_fase = f"RONDA DE {2**ronda}"
            
            n_duelos = 2 ** (ronda - 1)
            
            html_rondas += f"<div class='ronda'>\n"
            html_rondas += f"<div class='header-ronda'>{nombre_fase}</div>\n"
            
            for i in range(n_duelos):
                html_rondas += "<div class='duelo'>\n"
                
                if ronda == n_rondas: 
                    esg_a = nombres_ordenados[i * 2]
                    esg_b = nombres_ordenados[i * 2 + 1]
                else: 
                    esg_a = "Por definir"
                    esg_b = "Por definir"
                
                html_rondas += f"<div class='esgrimista'>{esg_a}</div>\n"
                html_rondas += f"<div class='esgrimista'>{esg_b}</div>\n"
                html_rondas += "</div>\n"
                
            html_rondas += "</div>\n"

        html_final = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta http-equiv="refresh" content="10">
            <title>Fixture en Vivo - {self.nombre}</title>
            <style> 
                body {{ font-family: Georgia, serif; background-color: #ffffff; margin: 20px; }}
                h1 {{ color: #940101; text-align: center; text-transform: uppercase; margin-bottom: 40px; letter-spacing: 1px; }}
                
                /* Contenedor principal alineado horizontalmente */
                .bracket-container {{ 
                    display: flex; 
                    flex-direction: row; 
                    justify-content: center; 
                    align-items: stretch; 
                    gap: 30px; 
                }}
                
                /* Cada columna de la fase */
                .ronda {{ 
                    display: flex; 
                    flex-direction: column; 
                    justify-content: space-around; 
                }}
                
                /* Títulos en rojo */
                .header-ronda {{ 
                    color: #940101; 
                    font-size: 18px; 
                    font-weight: bold; 
                    text-align: center; 
                    margin-bottom: 25px; 
                }}
                
                /* Contenedor de cada combate */
                .duelo {{ 
                    display: flex; 
                    flex-direction: column; 
                    justify-content: center; 
                    margin-bottom: 20px; 
                }}
                
                /* Cajitas azules con texto blanco */
                .esgrimista {{ 
                    background-color: #2c3e50; 
                    color: #ffffff; 
                    padding: 10px 15px; 
                    width: 220px; 
                    border-radius: 4px; 
                    font-size: 14px; 
                    margin: 2px 0;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
                    white-space: nowrap;
                    overflow: hidden;
                    text-overflow: ellipsis;
                }}
                
                .footer-bronce {{
                    margin-top: 50px;
                    text-align: center;
                }}
            </style>
        </head>
        <body>
            <h1>Federación HEMA Chile<br><span style="font-size: 24px; color: #2c3e50;">Cuadro Eliminatorio - {self.nombre}</span></h1>
            
            <div class="bracket-container">
                {html_rondas}
            </div>
            
            <!-- Combate por el Bronce separado abajo para no romper la simetría de la llave principal -->
            <div class="footer-bronce">
                <h3 style="color: #940101;">TERCER LUGAR</h3>
                <div style="display: inline-block; text-align: left;">
                    <div class="esgrimista">Perdedor Semifinal 1</div>
                    <div class="esgrimista">Perdedor Semifinal 2</div>
                </div>
            </div>
        </body>
        </html>
        """
        return html_final

    def generar_index_html(self, etapa="Grupos") -> str:
        if etapa == "Grupos":
            texto_etapa = "Fase Grupal"
            clase_etapa = "color-azul"
            titulo_seccion = "Fase Grupal - Tabla de posiciones en vivo"
            
            clasificados_set = self.obtener_clasificados()
            def resaltar_clasificados(row):
                es_clasificado = any(row['Esgrimista'] == c.nombre for c in clasificados_set)
                return ['background-color: #d4efdf' if es_clasificado else ''] * len(row)

            contenido_dinamico = "<div class='contenedor-tablas'>\n"
            for g in self.grupos:
                clasificacion = g.posiciones()
                filas = [{"Posición": i + 1, "Esgrimista": e.nombre, "Club": e.club, "Puntos": e.puntos_totales, "Dif.": e.diferencia_total} for i, e in enumerate(clasificacion)]
                df_grupo = pd.DataFrame(filas)
                styler = df_grupo.style.hide(axis='index').apply(resaltar_clasificados, axis=1).set_caption(f"Grupo {g.numero}").set_table_styles([
                    {'selector': 'caption', 'props': [('color', '#1a252f'), ('font-size', '18px'), ('font-weight', 'bold'), ('padding', '8px')]},
                    {'selector': 'th', 'props': [('background-color', "#940101"), ('color', 'white'), ('font-weight', 'bold'), ('text-align', 'center')]},
                    {'selector': 'td', 'props': [('text-align', 'center'), ('padding', '8px'), ('border-bottom', '1px solid #ddd')]}
                ]).set_properties(subset=['Esgrimista', 'Club'], **{'text-align': 'left'})
                contenido_dinamico += f"<div class='tarjeta-grupo'>\n{styler.to_html()}\n</div>\n"
            contenido_dinamico += "</div>\n"

        else: 
            texto_etapa = "Fase Eliminatoria"
            clase_etapa = "color-rojo"
            titulo_seccion = "Fase Eliminatoria - Fixture en vivo"
            
            import math
            clasificados_set = self.obtener_clasificados()
            n_clasificados = len(clasificados_set)

            if n_clasificados < 2:
                contenido_dinamico = "<h2 style='color: #940101; text-align: center;'>Aún no hay suficientes clasificados.</h2>"
            else:
                clasificados_ordenados = sorted(list(clasificados_set), key=lambda e: (e.puntos_totales, e.diferencia_total), reverse=True)
                n_rondas = math.ceil(math.log2(n_clasificados))
                n_slots = 2 ** n_rondas

                nombres_jugadores = [e.nombre for e in clasificados_ordenados]
                while len(nombres_jugadores) < n_slots: nombres_jugadores.append("BYE (Pasa Libre)")

                def generar_orden_bracket(n):
                    if n == 1: return [1]
                    mitad = generar_orden_bracket(n // 2)
                    return [val for semilla in mitad for val in (semilla, n + 1 - semilla)]

                nombres_ordenados = [nombres_jugadores[i - 1] for i in generar_orden_bracket(n_slots)]

                html_rondas = ""
                for ronda in range(n_rondas, 0, -1):
                    if ronda == 1: nombre_fase = "FINAL"
                    elif ronda == 2: nombre_fase = "SEMIFINAL"
                    elif ronda == 3: nombre_fase = "CUARTOS DE FINAL"
                    elif ronda == 4: nombre_fase = "OCTAVOS DE FINAL"
                    else: nombre_fase = f"RONDA DE {2**ronda}"
                    
                    html_rondas += f"<div class='ronda'>\n<div class='header-ronda'>{nombre_fase}</div>\n"
                    for i in range(2 ** (ronda - 1)):
                        html_rondas += "<div class='duelo'>\n"
                        esg_a = nombres_ordenados[i * 2] if ronda == n_rondas else "Por definir"
                        esg_b = nombres_ordenados[i * 2 + 1] if ronda == n_rondas else "Por definir"
                        html_rondas += f"<div class='esgrimista'>{esg_a}</div>\n<div class='esgrimista'>{esg_b}</div>\n</div>\n"
                    html_rondas += "</div>\n"

                contenido_dinamico = f"<div class='bracket-container'>\n{html_rondas}\n</div>"
                contenido_dinamico += """
                <div class='footer-bronce'>
                    <h3 style='color: #940101;'>TERCER LUGAR</h3>
                    <div style='display: inline-block; text-align: left;'>
                        <div class='esgrimista'>Perdedor Semifinal 1</div>
                        <div class='esgrimista'>Perdedor Semifinal 2</div>
                    </div>
                </div>"""

        css = """
            body { font-family: Georgia, serif; margin: 0; padding: 0; background-color: #ffffff; position: relative; min-height: 100vh; z-index: 0; }
            
            /* Marca de agua (Bandera) */
            body::before {
                content: ""; position: absolute; top: 0; left: 0; width: 100%; height: 100%;
                background-image: url('./assets/images/bandera_chile.png'); background-repeat: no-repeat; background-position: center; background-size: cover;
                opacity: 0.1; z-index: -1;
            }
            
            /* Encabezado Gris */
            .header-top { background-color: #f4f6f7; text-align: center; padding: 25px 20px; position: relative; border-bottom: 2px solid #ddd; }
            .logo { position: absolute; top: 20px; left: 30px; width: 100px; height: auto; }
            .header-top h1 { color: #000000; margin: 0; font-size: 32px; font-weight: bold; }
            .header-top h2 { color: #000000; margin: 8px 0; font-size: 24px; font-weight: normal; }
            .header-top h3 { color: #940101; margin: 12px 0 0 0; font-size: 20px; }
            
            /* Contenido */
            .content { padding: 40px 20px; text-align: center; }
            .info-text { font-size: 22px; font-weight: bold; margin: 15px 0; }
            .color-azul { color: #2c3e50; }
            .color-rojo { color: #940101; }
            .color-negro { color: #000000; }
            
            /* Estilos Tablas */
            .contenedor-tablas { display: flex; flex-wrap: wrap; gap: 30px; justify-content: center; align-items: flex-start; }
            .tarjeta-grupo { background-color: rgba(255, 255, 255, 0.95); padding: 15px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
            
            /* Estilos Bracket Eliminatorio */
            .bracket-container { display: flex; flex-direction: row; justify-content: center; align-items: stretch; gap: 30px; margin-top: 30px; }
            .ronda { display: flex; flex-direction: column; justify-content: space-around; }
            .header-ronda { color: #940101; font-size: 18px; font-weight: bold; text-align: center; margin-bottom: 25px; }
            .duelo { display: flex; flex-direction: column; justify-content: center; margin-bottom: 20px; }
            .esgrimista { background-color: #2c3e50; color: #ffffff; padding: 10px 15px; width: 220px; border-radius: 4px; font-size: 14px; margin: 2px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.2); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; text-align: left; }
            .footer-bronce { margin-top: 50px; text-align: center; }
        """

        html_final = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="utf-8">
    <meta http-equiv="refresh" content="10">
    <title>Torneo HEMA Chile - Seguimiento en Vivo</title>
    <style>{css}</style>
</head>
<body>
    <div class="header-top">
        <img src="./assets/images/hema_chile_logo.png" alt="Logo HEMA Chile" class="logo" onerror="this.onerror=null; this.src='./assets/icons/logo_hemachile.ico';">
        <h1>Torneo de Novatos HEMA Chile</h1>
        <h2>Edición 2026</h2>
        <h3>Seguimiento en Vivo</h3>
    </div>
    
    <div class="content">
        <div class="info-text color-azul">Categoría en desarrollo: {self.nombre}</div>
        <div class="info-text color-azul">Etapa en desarrollo: <span class="{clase_etapa}">{texto_etapa}</span></div>
        
        <h2 class="color-negro" style="margin-top: 50px; margin-bottom: 40px; font-size: 26px;">{titulo_seccion}</h2>
        {contenido_dinamico}
    </div>
</body>
</html>"""
        return html_final

    
    def __repr__(self):
        return f"Categoria: {self.nombre} | Inscritos: {len(self.esgrimistas)} | Grupos: {len(self.grupos)}"


#####################################################
## CONFIGURACIÓN DE LA GUI
#####################################################

class PantallaCarga:
    def __init__(self, pagina_principal):
        self.pagina_principal = pagina_principal
        self.pagina_principal.geometry("1000x700")
        self.pagina_principal.minsize(1000, 700)
        self.pagina_principal.title("Diseñador de Torneos - Prototipo")
        self.pagina_principal.config(background = "#E8E2E2")

        if sys.platform.startswith("win"):
            if os.path.exists("../assets/icons/logo_hemachile.ico"):
                self.pagina_principal.iconbitmap("../assets/icons/logo_hemachile.ico")
        else:
            if os.path.exists("../assets/images/logo_hemachile.png"):
                icono = PhotoImage(file = "../assets/images/logo_hemachile.png")
                self.pagina_principal.iconphoto(True, icono)
                
        self.construir_interfaz_carga()

    def construir_interfaz_carga(self):
        marco_centro = Frame(self.pagina_principal, bg="#E8E2E2")
        marco_centro.pack(expand=True)

        marco_titulo = Frame(marco_centro, bg="#E8E2E2")
        marco_titulo.pack(pady=(0, 5))

        self.logo_img = None
        if os.path.exists("../assets/images/logo_hemachile.png"):
            try:
                imagen_raw = Image.open("../assets/images/logo_hemachile.png")
                imagen_raw = imagen_raw.resize((70, 70), Image.Resampling.LANCZOS)
                self.logo_img = ImageTk.PhotoImage(imagen_raw)
                Label(marco_titulo, image=self.logo_img, bg="#E8E2E2").pack(side=LEFT, padx=(0, 15))
            except Exception:
                pass

        Label(
            marco_titulo, 
            text="Torneo de Novatos\nHEMA Chile 2026", 
            font=("Georgia", 22, "bold"), 
            bg="#E8E2E2", 
            fg="#2c3e50",
            justify=LEFT
        ).pack(side=LEFT)

        Label(
            marco_centro,
            text="Prototipo 0.4.1",
            font=("Georgia", 11, "italic"),
            bg="#E8E2E2",
            fg="#7f8c8d"
        ).pack(pady=(0, 35))

        boton_entrar = Button(
            marco_centro,
            text="Comenzar",
            command=self.lanzar_app_principal,
            font=("Georgia", 14, "bold"),
            bg="#940101",
            fg="white",
            padx=20,
            pady=12,
            relief=RAISED
        )
        boton_entrar.pack(pady=10)

    def lanzar_app_principal(self):
        for widget in self.pagina_principal.winfo_children():
            widget.destroy()
        
        InterfazTorneo(self.pagina_principal)


class InterfazTorneo:
    def __init__(self, pagina_principal):
        self.pagina_principal = pagina_principal
        self.pagina_principal.geometry("1000x700")
        self.pagina_principal.minsize(1000, 700)
        self.pagina_principal.title("Diseñador de Torneos - Prototipo")
        self.pagina_principal.config(background = "#E8E2E2")

        self.df_por_categorias = {}
        self.configuracion_torneo = {}
        self.categorias_procesadas = {}

        if sys.platform.startswith("win"):
            if os.path.exists("../assets/icons/logo_hemachile.ico"):
                self.pagina_principal.iconbitmap("../assets/icons/logo_hemachile.ico")
        else:
            if os.path.exists("../assets/images/logo_hemachile.png"):
                icono = PhotoImage(file = "../assets/images/logo_hemachile.png")
                self.pagina_principal.iconphoto(True, icono)
        self.construir_ventana_principal()

    def construir_ventana_principal(self):
        self.marco_izquierdo = Frame(self.pagina_principal, bg='#E8E2E2', padx=20, pady=20)
        self.marco_izquierdo.pack(side = LEFT, fill = BOTH, expand = True)

        self.boton_cargar_csv = Button(
            self.marco_izquierdo,
            text = "Cargar archivo csv",
            command = self.cargar_csv,
            font = ("Georgia", 12),
            bg = "#2c3e50",
            fg = "white"
        )
        self.boton_cargar_csv.pack(pady=(0, 15), fill = X)

        self.marco_resumen = LabelFrame(
            self.marco_izquierdo,
            text = "Inscritos por categoría",
            bg = "#E8E2E2",
            font = ("Georgia", 10, "bold")
        )
        self.marco_resumen.pack(fill = BOTH, expand = True)

        self.texto_resumen = Text(self.marco_resumen, width = 40, height = 15, state = DISABLED, bg = "#f4f6f7")
        self.texto_resumen.pack(padx = 5, pady = 5, fill = BOTH, expand = True)

        self.boton_configurar_torneo = Button(
            self.marco_izquierdo,
            text = "Configurar torneo",
            command = self.abrir_ventana_configuracion,
            font = ("Georgia", 12, "bold"),
            bg = "#940101",
            fg = "white",
            state = DISABLED
        )
        self.boton_configurar_torneo.pack(pady = (15,0), fill = X)

        self.boton_exportar_config = Button(
            self.marco_izquierdo,
            text = "Exportar configuración",
            command = self.exportar_configuracion,
            font = ("Georgia", 12, "bold"),
            bg = "#940101",
            fg = "white",
            state = DISABLED 
        )
        self.boton_exportar_config.pack(pady = (15,0), fill = X)

        self.boton_importar_config = Button(
            self.marco_izquierdo,
            text = "Importar configuración",
            command = self.importar_configuracion,
            font = ("Georgia", 12, "bold"),
            bg = "#940101",
            fg = "white"
        )
        self.boton_importar_config.pack(pady = (15,0), fill = X)

        self.marco_derecho = Frame(self.pagina_principal, bg='#E8E2E2', padx=20, pady=20)
        self.marco_derecho.pack(side = RIGHT, fill = BOTH, expand = True)

        self.boton_exportar_excel = Button(
            self.marco_derecho,
            text = "Exportar fichas de duelos",
            command = self.exportar_excel_duelos,
            font = ("Georgia", 12, "bold"),
            bg = "#940101",
            fg = "white",
        )
        self.boton_exportar_excel.pack(pady=(0, 15), fill = X)

        Label(self.marco_derecho, text="Gestión de Torneos", bg='#E8E2E2', font=("Georgia", 12, "bold")).pack(pady=(25, 5))

        marco_gestion = Frame(self.marco_derecho, bg='#E8E2E2')
        marco_gestion.pack(fill=X)

        self.combo_gestion = ttk.Combobox(marco_gestion, state="readonly")
        self.combo_gestion.pack(side=LEFT, fill=X, expand=True, padx=(0, 10))

        self.boton_iniciar_gestion = Button(
            marco_gestion,
            text="Iniciar Torneo",
            command=self.abrir_gestion_torneo,
            font=("Georgia", 11, "bold"),
            bg="#940101",
            fg="white"
        )
        self.boton_iniciar_gestion.pack(side=RIGHT)

    def cargar_csv(self):
        ruta_archivo = filedialog.askopenfilename(
            title = "Seleccionar archivo de inscritos",
            filetypes = [("Archivos CSV", "*.csv")]
        )
        if not ruta_archivo:
            return

        try:
            df = pd.read_csv(ruta_archivo)
            df['Categoria'] = df['Categoria'].str.split(';')
            df_expandido = df.explode('Categoria')
            df_expandido['Categoria'] = df_expandido['Categoria'].str.strip()

            self.df_por_categorias.clear()
            resumen = ""

            for nombre_cat, grupo_df in df_expandido.groupby('Categoria'):
                self.df_por_categorias[nombre_cat] = grupo_df[['Nombre', 'Club']].copy()
                resumen += f"{nombre_cat}: {len(self.df_por_categorias[nombre_cat])} inscritos\n"

            self.texto_resumen.config(state = NORMAL)
            self.texto_resumen.delete(1.0, END)
            self.texto_resumen.insert(END, resumen)
            self.texto_resumen.config(state = DISABLED)

            self.boton_configurar_torneo.config(state = NORMAL)

        except Exception as e:
            messagebox.showerror("Error", f"No se pudo procesar el archivo:\n{e}")

    def abrir_ventana_configuracion(self):
        self.ventana_config = Toplevel(self.pagina_principal)
        self.ventana_config.title("Configuración de Grupos")
        ## self.ventana_config.geometry("450x250")
        self.ventana_config.config(bg = "#E8E2E2", padx = 20, pady = 20)

        self.ventana_config.transient(self.pagina_principal)

        Label(self.ventana_config, text="Seleccione una categoría", bg="#E8E2E2", font=("Georgia", 11)).pack(anchor=W)

        lista_categorias = list(self.df_por_categorias.keys())
        combo_categorias = ttk.Combobox(self.ventana_config, values = lista_categorias, state="readonly", width=40)
        combo_categorias.pack(pady = 5, anchor = W)
        if lista_categorias:
            combo_categorias.current(0)

        Button(
            self.ventana_config,
            text = "Configurar Grupos",
            command = lambda: self.abrir_ventana_grupos(combo_categorias.get()),
            bg = "#2c3e50", fg = "white"
        ).pack(pady = 10, anchor = W)

        Button(
            self.ventana_config,
            text = "Exportar Distribución html",
            command = self.exportar_html,
            bg = "#940101", fg = "white", font = ("Arial", 11, "bold")
        ).pack(side = BOTTOM, fill = X, pady = 10)

    def abrir_ventana_grupos(self, categoria):
        if not categoria:
            return

        total_inscritos = len(self.df_por_categorias[categoria])

        ventana_grupos = Toplevel(self.pagina_principal)
        ventana_grupos.title(f"Grupos - {categoria}")
       ## ventana_grupos.geometry("450x200")
        ventana_grupos.config(bg = "#E8E2E2", padx = 20, pady = 20)

        ventana_grupos.transient(self.ventana_config)
        ventana_grupos.grab_set()

        Label(ventana_grupos, text=f"Inscritos totales: {total_inscritos}", bg = "#E8E2E2", font = ("Georgia", 11, "bold")).pack(pady = 5)
        Label(ventana_grupos, text = "Ingrese formato de grupos (ej: 4,4,4 para 3 grupos de 4 integrantes):", bg = "#E8E2E2").pack(pady = 5)

        entrada_grupos = Entry(ventana_grupos, width = 20, font = ("Georgia", 12), justify = CENTER)
        entrada_grupos.pack(pady = 5)

        if categoria in self.configuracion_torneo:
            config_actual = ",".join(map(str, self.configuracion_torneo[categoria]))
            entrada_grupos.insert(0, config_actual)

        def guardar_configuracion():
            texto = entrada_grupos.get()
            try:
                capacidades = [int(x.strip()) for x in texto.split(",")]
                if sum(capacidades) != total_inscritos:
                    messagebox.showerror("Error", "La cantidad de cupos requeridos no coincide con la cantidad de inscritos en la categoría")
                    ventana_grupos.focus_force()
                    return
                if any(cap not in [3,4,5] for cap in capacidades):
                    messagebox.showwarning("Advertencia", "Se recomiendan grupos de 3, 4 o 5 personas únicamente.")

                self.configuracion_torneo[categoria] = capacidades
                if categoria in self.categorias_procesadas:
                    del self.categorias_procesadas[categoria]
                
                messagebox.showinfo("Guardado", f"Configuración guardada para {categoria}")
                ventana_grupos.destroy()

            except ValueError:
                messagebox.showerror("Error de formato", "Use únicamente números separados por comas (ej: 4,4,3,5)")
                ventana_grupos.focus_force()

        Button(
            ventana_grupos,
            text = "Guardar",
            command = guardar_configuracion,
            bg = "#2c3e50",
            fg = "white"
        ).pack(pady=15)

    def actualizar_combo_gestion(self):
        categorias_list = list(self.categorias_procesadas.keys())
        self.combo_gestion['values'] = categorias_list
        if categorias_list:
            self.combo_gestion.current(0)

    def exportar_html(self):
        if not self.configuracion_torneo:
            messagebox.showwarning("Faltan datos", "No hay ninguna categoría configurada para exportar")
            return

        directorio_destino = filedialog.askdirectory(title="Seleccionar carpeta de destino")
        if not directorio_destino:
            return

        try:
            
            for nombre_cat, capacidades in self.configuracion_torneo.items():

                if nombre_cat in self.categorias_procesadas:
                    cat = self.categorias_procesadas[nombre_cat]

                else:
                    df_grupo = self.df_por_categorias[nombre_cat]
                    cat = Categoria(nombre_cat)
                    cat.cargar_esgrimistas(df_grupo)
                    cat.configurar_grupos(capacidades)
                    cat.generar_grupos()

                    for grupo in cat.grupos:
                        grupo.generar_duelos()
                    
                    self.categorias_procesadas[nombre_cat] = cat

                html_distribucion = cat.generar_html_distribucion()
                nombre_archivo = f"grupos_{nombre_cat.lower().replace(' ','_')}.html"
                ruta_completa = os.path.join(directorio_destino, nombre_archivo)

                with open(ruta_completa, 'w', encoding='utf-8') as file:
                    file.write(html_distribucion)

            messagebox.showinfo("Éxito", f"Todos los archivos html se exportaron correctamente")
            self.boton_exportar_config.config(state=NORMAL)
            self.actualizar_combo_gestion()

        except Exception as e:
            messagebox.showerror("Error de exportación", str(e))

    def ordenar_duelos_con_descanso(self, grupo):
        n = len(grupo.integrantes)
        
        if n == 3:
            orden_optimo = [(0, 1), (1, 2), (0, 2)]
        elif n == 4:
            orden_optimo = [(0, 3), (1, 2), (0, 2), (1, 3), (2, 3), (0, 1)]
        elif n == 5:
            orden_optimo = [(0, 1), (2, 3), (4, 0), (1, 2), (4, 3), (0, 2), (1, 4), (3, 0), (2, 4), (3, 1)]
        else:
            return grupo.duelos
            
        duelos_ordenados = []
        for i, j in orden_optimo:
            esg_a = grupo.integrantes[i]
            esg_b = grupo.integrantes[j]
            
            for duelo in grupo.duelos:
                if (duelo.esgrimista_a == esg_a and duelo.esgrimista_b == esg_b) or \
                   (duelo.esgrimista_a == esg_b and duelo.esgrimista_b == esg_a):
                    
                    duelo.esgrimista_a = esg_a
                    duelo.esgrimista_b = esg_b
                    
                    duelos_ordenados.append(duelo)
                    break
                    
        return duelos_ordenados

    def exportar_excel_duelos(self):
        if not self.categorias_procesadas:
            messagebox.showwarning("Atención", "Debes configurar los grupos y exportar la distribución HTML primero para fijar los asaltos.")
            return
            
        directorio_destino = filedialog.askdirectory(title="Seleccionar carpeta de destino")
        if not directorio_destino:
            return
            
        try:
            for nombre_cat, cat in self.categorias_procesadas.items():
                ruta_completa = os.path.join(directorio_destino, f"fichas_duelos_{nombre_cat.lower().replace(' ','_')}.xlsx")
                
                with pd.ExcelWriter(ruta_completa, engine='openpyxl') as writer:
                    for grupo in cat.grupos:
                        duelos_ordenados = self.ordenar_duelos_con_descanso(grupo)
                        
                        filas = []
                        for duelo in duelos_ordenados:
                            filas.append({
                                "Sanciones Rojo": "",
                                "Esgrimista Rojo": duelo.esgrimista_a.nombre,
                                "Intercambios Rojo": "",
                                " VS ": "-",
                                "Intercambios Azul": "",
                                "Esgrimista Azul": duelo.esgrimista_b.nombre,
                                "Sanciones Azul": ""
                            })
                            
                        df_grupo = pd.DataFrame(filas)
                        df_grupo.to_excel(writer, sheet_name=f"Grupo {grupo.numero}", index=False)
                        
            messagebox.showinfo("Épico", "Las fichas de duelo han sido exportadas correctamente.")
            
        except Exception as e:
            messagebox.showerror("Error", f"Ocurrió un error al exportar Excel:\n{str(e)}")

    def exportar_configuracion(self):
        if not self.categorias_procesadas:
            messagebox.showwarning("Atención", "No hay un torneo procesado en memoria para exportar.")
            return

        ruta_archivo = filedialog.asksaveasfilename(
            title="Guardar configuración del torneo",
            defaultextension=".dtpa",
            filetypes=[("Archivos de Torneo DTPA", "*.dtpa"), ("Todos los archivos", "*.*")]
        )
        if not ruta_archivo:
            return

        try:
            estado_torneo = {
                'df_por_categorias': self.df_por_categorias,
                'configuracion_torneo': self.configuracion_torneo,
                'categorias_procesadas': self.categorias_procesadas
            }
            
            with open(ruta_archivo, 'wb') as archivo:
                pickle.dump(estado_torneo, archivo)
                
            messagebox.showinfo("Éxito", "La configuración del torneo se ha guardado correctamente.")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo exportar la configuración:\n{str(e)}")

    def importar_configuracion(self):
        ruta_archivo = filedialog.askopenfilename(
            title="Seleccionar configuración de torneo",
            filetypes=[("Archivos de Torneo DTPA", "*.dtpa"), ("Todos los archivos", "*.*")]
        )
        if not ruta_archivo:
            return

        try:
            with open(ruta_archivo, 'rb') as archivo:
                estado_torneo = pickle.load(archivo)

            self.df_por_categorias = estado_torneo.get('df_por_categorias', {})
            self.configuracion_torneo = estado_torneo.get('configuracion_torneo', {})
            self.categorias_procesadas = estado_torneo.get('categorias_procesadas', {})

            resumen = ""
            for nombre_cat, df in self.df_por_categorias.items():
                resumen += f"{nombre_cat}: {len(df)} inscritos\n"

            self.texto_resumen.config(state = NORMAL)
            self.texto_resumen.delete(1.0, END)
            if resumen:
                self.texto_resumen.insert(END, resumen)
            else:
                self.texto_resumen.insert(END, "Torneo cargado sin datos de resumen.")
            self.texto_resumen.config(state = DISABLED)

            self.boton_configurar_torneo.config(state = NORMAL)
            self.boton_exportar_config.config(state = NORMAL)
            self.actualizar_combo_gestion()

            messagebox.showinfo("Épico", "COnfiguración de torneo importada exitosamente.")

        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar el archivo de torneo:\n{str(e)}")


    def abrir_gestion_torneo(self):
        categoria_seleccionada = self.combo_gestion.get()
        if not categoria_seleccionada:
            messagebox.showwarning("Atención", "Selecciona una categoría procesada primero.")
            return

        cat = self.categorias_procesadas[categoria_seleccionada]
        
        ventana_gestion = Toplevel(self.pagina_principal)
        ventana_gestion.title(f"Configuración de Torneo - {categoria_seleccionada}")
        ## ventana_gestion.geometry("700x500")
        ventana_gestion.config(bg="#E8E2E2", padx=20, pady=20)
        ventana_gestion.transient(self.pagina_principal)
        ventana_gestion.grab_set()

        Label(ventana_gestion, text=f"Inscritos totales: {len(cat.esgrimistas)}", bg="#E8E2E2", font=("Georgia", 11, "bold")).pack(anchor=W)
        Label(ventana_gestion, text=f"Grupos: {len(cat.grupos)}", bg="#E8E2E2", font=("Georgia", 11, "bold")).pack(anchor=W, pady=(0, 15))

        marco_botones_ver = Frame(ventana_gestion, bg="#E8E2E2")
        marco_botones_ver.pack(fill=X, pady=5)

        Button(marco_botones_ver, text="Ver Grupos", command=lambda: self.ver_grupos_interfaz(cat, ventana_gestion), bg="#2c3e50", fg="white", font=("Georgia", 10)).pack(side=LEFT, expand=True, fill=X, padx=(0, 5))
        Button(marco_botones_ver, text="Ver inscritos", command=lambda: self.ver_inscritos_interfaz(cat, ventana_gestion), bg="#2c3e50", fg="white", font=("Georgia", 10)).pack(side=LEFT, expand=True, fill=X, padx=(5, 0))

        Label(ventana_gestion, text="Configurar clasificados", bg="#E8E2E2", font=("Georgia", 12, "bold")).pack(anchor=W, pady=(25, 10))

        marco_fijos = Frame(ventana_gestion, bg="#E8E2E2")
        marco_fijos.pack(fill=X, pady=2)
        Label(marco_fijos, text="Cupos fijos de clasificación por grupo:", bg="#E8E2E2").pack(side=LEFT)
        combo_fijos = ttk.Combobox(marco_fijos, values=list(range(0, 6)), state="readonly", width=5)
        combo_fijos.pack(side=RIGHT)
        combo_fijos.current(0)

        marco_check = Frame(ventana_gestion, bg="#E8E2E2")
        marco_check.pack(fill=X, pady=2)
        Label(marco_check, text="Regla de mejores terceros:", bg="#E8E2E2").pack(side=LEFT)
        var_terceros = BooleanVar()

        marco_terceros = Frame(ventana_gestion, bg="#E8E2E2")
        marco_terceros.pack(fill=X, pady=2)
        Label(marco_terceros, text="Mejores 'terceros' clasificados:", bg="#E8E2E2").pack(side=LEFT)
        combo_terceros = ttk.Combobox(marco_terceros, values=list(range(1, 6)), state="disabled", width=5)
        combo_terceros.pack(side=RIGHT)
        combo_terceros.current(0)

        def alternar_terceros():
            if var_terceros.get():
                combo_terceros.config(state="readonly")
            else:
                combo_terceros.config(state="disabled")

        Checkbutton(marco_check, variable=var_terceros, command=alternar_terceros, bg="#E8E2E2").pack(side=RIGHT)

        Label(ventana_gestion, text="El concepto de terceros es extensible a cuartos, quintos, entre otros según corresponda a cada caso", bg="#E8E2E2", font=("Arial", 8, "italic"), fg="#7f8c8d").pack(anchor=W, pady=(5, 20))

        def iniciar_con_configuracion():
            try:
                fijos = int(combo_fijos.get())
                usar_terc = var_terceros.get()
                n_terc = int(combo_terceros.get()) if usar_terc else 0
            except ValueError:
                fijos, usar_terc, n_terc = 0, False, 0
                
            self.abrir_panel_de_torneo(ventana_gestion, cat, fijos, usar_terc, n_terc)

        Button(ventana_gestion, text="Iniciar Torneo", command=iniciar_con_configuracion, bg="#940101", fg="white", font=("Georgia", 12, "bold"), padx=15).pack(side=BOTTOM, anchor=E)

    def ver_inscritos_interfaz(self, cat, ventana_padre):
        ventana_insc = Toplevel(ventana_padre)
        ventana_insc.title(f"Inscritos - {cat.nombre}")
        ## ventana_insc.geometry("500x400")
        
        ventana_insc.transient(ventana_padre)
        ventana_insc.grab_set()
        
        arbol = ttk.Treeview(ventana_insc, columns=("Nombre", "Club"), show='headings')
        arbol.heading("Nombre", text="Nombre")
        arbol.heading("Club", text="Club")
        arbol.column("Nombre", width=200)
        arbol.column("Club", width=250)
        
        arbol.tag_configure("par", background="#f4f6f7")
        arbol.tag_configure("impar", background="#ffffff")
        
        for i, esg in enumerate(cat.esgrimistas):
            etiqueta = "par" if i % 2 == 0 else "impar"
            arbol.insert("", "end", values=(esg.nombre, esg.club), tags=(etiqueta,))
            
        scrollbar = ttk.Scrollbar(ventana_insc, orient=VERTICAL, command=arbol.yview)
        arbol.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=RIGHT, fill=Y)
        arbol.pack(fill=BOTH, expand=True)
        

    def ver_grupos_interfaz(self, cat, ventana_padre):
        ventana_grupos = Toplevel(ventana_padre)
        ventana_grupos.title(f"Grupos - {cat.nombre}")
       ## ventana_grupos.geometry("500x500")
        
        ventana_grupos.transient(ventana_padre)
        ventana_grupos.grab_set()
        
        arbol = ttk.Treeview(ventana_grupos, columns=("Nombre", "Club"), show='headings')
        arbol.heading("Nombre", text="Nombre")
        arbol.heading("Club", text="Club")
        arbol.column("Nombre", width=200)
        arbol.column("Club", width=250)
        
        arbol.tag_configure("encabezado_grupo", background="#2c3e50", foreground="white")
        arbol.tag_configure("separador", background="#E8E2E2")
        
        for grupo in cat.grupos:
            arbol.insert("", "end", values=(f"GRUPO {grupo.numero}", ""), tags=("encabezado_grupo",))
            
            for esg in grupo.integrantes:
                arbol.insert("", "end", values=(esg.nombre, esg.club))
                
            arbol.insert("", "end", values=("", ""), tags=("separador",))
                
        scrollbar = ttk.Scrollbar(ventana_grupos, orient=VERTICAL, command=arbol.yview)
        arbol.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=RIGHT, fill=Y)
        arbol.pack(fill=BOTH, expand=True)

    def abrir_panel_de_torneo(self, ventana_previa, cat_actual, fijos, usar_terc, n_terc):
        ventana_previa.destroy()
        
        cat_actual.cupos_fijos = fijos
        cat_actual.usar_terceros = usar_terc
        cat_actual.cupos_terceros = n_terc
        
        panel_torneo = Toplevel(self.pagina_principal)
        panel_torneo.title(f"Panel de Torneo en Vivo - {cat_actual.nombre}")
        panel_torneo.geometry("850x650")
        panel_torneo.config(bg="#E8E2E2")
        
        label_status_web = Label(panel_torneo, text="Apagado", font=("Georgia", 11, "bold"), fg="#7f8c8d", bg="#E8E2E2")
        
        Label(panel_torneo, text="Fase de Grupos", font=("Georgia", 16, "bold"), bg="#E8E2E2").pack(pady=(15, 5))
        
        marco_grupos = Frame(panel_torneo, bg="#E8E2E2")
        marco_grupos.pack(fill=X, padx=20, pady=5)
        for grupo in cat_actual.grupos:
            Button(marco_grupos, text=f"Grupo {grupo.numero}", command=lambda g=grupo: self.abrir_ventana_grupo(cat_actual, g, panel_torneo), bg="#2c3e50", fg="white", font=("Georgia", 11)).pack(side=LEFT, expand=True, padx=5)
            
        marco_opciones_grupos = Frame(panel_torneo, bg="#E8E2E2")
        marco_opciones_grupos.pack(fill=X, padx=20, pady=10)
        
        fila1_g = Frame(marco_opciones_grupos, bg="#E8E2E2")
        fila1_g.pack(fill=X, pady=2)
        Button(fila1_g, text="Gestión de Sanciones", command=lambda: self.abrir_gestion_sanciones(cat_actual, panel_torneo), bg="#2c3e50", fg="white", font=("Georgia", 11, "bold")).pack(side=LEFT, expand=True, padx=5)
        Button(fila1_g, text="Tabla de posiciones", command=lambda: self.abrir_tabla_posiciones(cat_actual, panel_torneo), bg="#940101", fg="white", font=("Georgia", 11, "bold")).pack(side=LEFT, expand=True, padx=5)
        
        fila2_g = Frame(marco_opciones_grupos, bg="#E8E2E2")
        fila2_g.pack(fill=X, pady=5)
        Button(fila2_g, text="Iniciar Broadcast (Grupos)", command=lambda: self.ejecutar_broadcast(cat_actual, "Grupos", label_status_web), bg="#27ae60", fg="white", font=("Georgia", 10, "bold")).pack(side=LEFT, expand=True, padx=5)
        Button(fila2_g, text="Terminar Broadcast", command=lambda: self.detener_broadcast(label_status_web), bg="#7f8c8d", fg="white", font=("Georgia", 10, "bold")).pack(side=LEFT, expand=True, padx=5)
        
        ttk.Separator(panel_torneo, orient=HORIZONTAL).pack(fill=X, padx=30, pady=15)
        
        Label(panel_torneo, text="Fase Eliminatoria", font=("Georgia", 16, "bold"), bg="#E8E2E2").pack(pady=(5, 5))
        
        marco_eliminatorias = Frame(panel_torneo, bg="#E8E2E2")
        marco_eliminatorias.pack(fill=X, padx=20, pady=10)
        
        fila1_e = Frame(marco_eliminatorias, bg="#E8E2E2")
        fila1_e.pack(fill=X, pady=2)
        Button(fila1_e, text="Duelos", command=lambda: self.abrir_duelos_eliminatorios(cat_actual, panel_torneo), bg="#2c3e50", fg="white", font=("Georgia", 11, "bold")).pack(side=LEFT, expand=True, padx=5)
        Button(fila1_e, text="Fixture", command=lambda: self.explorar_fixture_ete3(cat_actual, panel_torneo), bg="#940101", fg="white", font=("Georgia", 11, "bold")).pack(side=LEFT, expand=True, padx=5)
        
        fila2_e = Frame(marco_eliminatorias, bg="#E8E2E2")
        fila2_e.pack(fill=X, pady=5)
        Button(fila2_e, text="Iniciar Broadcast (Fixture)", command=lambda: self.ejecutar_broadcast(cat_actual, "Eliminatorias", label_status_web), bg="#27ae60", fg="white", font=("Georgia", 10, "bold")).pack(side=LEFT, expand=True, padx=5)
        Button(fila2_e, text="Terminar Broadcast", command=lambda: self.detener_broadcast(label_status_web), bg="#7f8c8d", fg="white", font=("Georgia", 10, "bold")).pack(side=LEFT, expand=True, padx=5)
        
        marco_inferior = Frame(panel_torneo, bg="#E8E2E2")
        marco_inferior.pack(side=BOTTOM, fill=X, padx=20, pady=20)
        
        marco_status = Frame(marco_inferior, bg="#E8E2E2")
        marco_status.pack(side=LEFT, padx=10)
        Label(marco_status, text="STATUS online: ", font=("Georgia", 11, "bold"), bg="#E8E2E2").pack(side=LEFT)
        label_status_web.pack(side=LEFT)
        
        Button(marco_inferior, text="Guardar", command=lambda: self.guardar_progreso_torneo(cat_actual), bg="#2c3e50", fg="white", font=("Georgia", 11, "bold"), width=15).pack(side=RIGHT, padx=5)
        Button(marco_inferior, text="Cargar", command=lambda: self.cargar_datos_torneo(cat_actual, panel_torneo), bg="#2c3e50", fg="white", font=("Georgia", 11, "bold"), width=15).pack(side=RIGHT, padx=5)
        Button(marco_inferior, text="Finalizar Torneo", command=lambda: messagebox.showinfo("Fin", "Función en construcción"), bg="#940101", fg="white", font=("Georgia", 11, "bold"), width=15).pack(side=RIGHT, padx=5)

    def cargar_datos_torneo(self, cat_actual, ventana_panel):
        ruta_archivo = filedialog.askopenfilename(
            title="Cargar configuración del torneo",
            filetypes=[("Archivos de Torneo DTPA", "*.dtpa"), ("Todos los archivos", "*.*")]
        )
        
        if ruta_archivo:
            try:
                with open(ruta_archivo, 'rb') as f:
                    categoria_cargada = pickle.load(f)
                if isinstance(categoria_cargada, dict):
                    cat_actual.__dict__.update(categoria_cargada)
                else:
                    cat_actual.__dict__.update(categoria_cargada.__dict__)
            
                messagebox.showinfo("Carga exitosa", "Los datos del torneo se han cargado correctamente.")
                ventana_panel.destroy()
                self.abrir_panel_de_torneo(
                    ventana_previa=Toplevel(), 
                    cat_actual=cat_actual, 
                    fijos=cat_actual.cupos_fijos, 
                    usar_terc=cat_actual.usar_terceros, 
                    n_terc=cat_actual.cupos_terceros
                )
                
            except Exception as e:
                messagebox.showerror("Error de lectura", f"No se pudo cargar el archivo:\n{str(e)}")

    def ventana_vacia(self, titulo, padre):
        vent = Toplevel(padre)
        vent.title(titulo)
      ##  vent.geometry("400x200")
        vent.transient(padre)
        Label(vent, text="Función en construcción", font=("Georgia", 12)).pack(expand=True)

    def guardar_progreso_torneo(self, cat_actual):
        nombre_sugerido = f"progreso_{cat_actual.nombre.replace(' ', '_')}.dtpa"
        
        ruta_archivo = filedialog.asksaveasfilename(
            title="Guardar progreso del torneo",
            initialfile=nombre_sugerido,
            defaultextension=".dtpa",
            filetypes=[("Archivos de Torneo DTPA", "*.dtpa"), ("Todos los archivos", "*.*")]
        )
        
        if ruta_archivo:
            try:
                with open(ruta_archivo, 'wb') as f:
                    pickle.dump(cat_actual, f)
                
                messagebox.showinfo("Guardado Exitoso", "El progreso de los duelos y tablas se ha respaldado correctamente.")
            except Exception as e:
                messagebox.showerror("Error al guardar", f"No se pudo guardar el progreso:\n{str(e)}")

    def abrir_ventana_grupo(self, cat, grupo, ventana_padre):
        vent = Toplevel(ventana_padre)
        vent.title(f"Duelos - Grupo {grupo.numero}")
       ## vent.geometry("850x650")
        vent.config(bg="#E8E2E2")
        vent.transient(ventana_padre)
        vent.grab_set()

        Label(vent, text="Duelos", font=("Georgia", 16, "bold"), bg="#E8E2E2").pack(pady=15)
        
        marco_duelos = Frame(vent, bg="#E8E2E2")
        marco_duelos.pack(fill=BOTH, expand=True, padx=20)

        def dibujar_duelos():
            for widget in marco_duelos.winfo_children():
                widget.destroy()
                
            for duelo in grupo.duelos:
                fila = Frame(marco_duelos, bg="#E8E2E2")
                fila.pack(fill=X, pady=6)
                
                texto_duelo = f"{duelo.esgrimista_a.nombre}   {duelo.puntaje_a_ingresado}  vs  {duelo.puntaje_b_ingresado}   {duelo.esgrimista_b.nombre}"
                Label(fila, text=texto_duelo, bg="#E8E2E2", font=("Georgia", 11), width=45, anchor=W).pack(side=LEFT)
                
                Button(fila, text="Ingresar|Modificar Resultado", command=lambda d=duelo: self.ingresar_resultado_duelo(cat, d, dibujar_duelos, vent), bg="#2c3e50", fg="white").pack(side=LEFT, padx=5)
                Button(fila, text="Registrar Sanciones", command=lambda d=duelo: self.registrar_sanciones_duelo(cat, d, vent), bg="#940101", fg="white").pack(side=LEFT, padx=5)

        dibujar_duelos()

        marco_botones = Frame(vent, bg="#E8E2E2")
        marco_botones.pack(fill=X, side=BOTTOM, pady=20, padx=30)
        Button(marco_botones, text="Guardar", command=lambda: self.guardar_progreso_torneo(cat), bg="#2c3e50", fg="white", font=("Georgia", 11, "bold")).pack(side=LEFT)
        Button(marco_botones, text="Cerrar", command=vent.destroy, bg="#2c3e50", fg="white", font=("Georgia", 11, "bold")).pack(side=RIGHT)


    def ingresar_resultado_duelo(self, cat, duelo, callback_redibujar, ventana_padre):
        vent = Toplevel(ventana_padre)
        vent.title("Resultado")
        vent.geometry("450x150")
        vent.minsize(600,150)
        vent.config(bg="#E8E2E2")
        vent.transient(ventana_padre)
        vent.grab_set()
        
        marco = Frame(vent, bg="#E8E2E2")
        marco.pack(expand=True)
        
        Label(marco, text=duelo.esgrimista_a.nombre, bg="#E8E2E2", font=("Georgia", 10)).grid(row=0, column=0, padx=5)
        entry_a = Entry(marco, width=5, justify=CENTER)
        entry_a.grid(row=0, column=1, padx=5)
        
        Label(marco, text="  VS  ", bg="#E8E2E2", font=("Georgia", 10, "bold")).grid(row=0, column=2)
        
        entry_b = Entry(marco, width=5, justify=CENTER)
        entry_b.grid(row=0, column=3, padx=5)
        Label(marco, text=duelo.esgrimista_b.nombre, bg="#E8E2E2", font=("Georgia", 10)).grid(row=0, column=4, padx=5)
        
        def guardar():
            try:
                pts_a = int(entry_a.get())
                pts_b = int(entry_b.get())
                duelo.asignar_resultado(pts_a, pts_b)
                
                self.actualizar_broadcast_silencioso(cat)
                
                callback_redibujar()
                vent.destroy()
            except ValueError:
                messagebox.showerror("Error", "Ingrese valores numéricos válidos.")
                
        Button(vent, text="Guardar", command=guardar, bg="#2c3e50", fg="white", font=("Georgia", 10, "bold")).pack(pady=10)

    def registrar_sanciones_duelo(self, cat, duelo, ventana_padre):
        vent = Toplevel(ventana_padre)
        vent.title("Sanciones de Duelo")
        vent.geometry("500x200")
        vent.config(bg="#E8E2E2")
        vent.transient(ventana_padre)
        vent.grab_set()
        
        duelo_str = f"{duelo.esgrimista_a.nombre} vs {duelo.esgrimista_b.nombre}"
        
        marco_a = Frame(vent, bg="#E8E2E2")
        marco_a.pack(fill=X, pady=15, padx=20)
        Label(marco_a, text=duelo.esgrimista_a.nombre, bg="#E8E2E2", width=25, anchor=W).pack(side=LEFT)
        Button(marco_a, text="Sanción leve", command=lambda: [duelo.registrar_falta_leve_a(), self.actualizar_broadcast_silencioso(cat), messagebox.showinfo("Sanción", "Leve registrada.", parent=vent)], bg="#2c3e50", fg="white").pack(side=LEFT, padx=5)
        Button(marco_a, text="Sanción Grave", command=lambda: [duelo.esgrimista_a.registrar_falta_grave(duelo_str=duelo_str), self.actualizar_broadcast_silencioso(cat), messagebox.showinfo("Sanción", "Grave registrada.", parent=vent)], bg="#940101", fg="white").pack(side=LEFT, padx=5)

        marco_b = Frame(vent, bg="#E8E2E2")
        marco_b.pack(fill=X, pady=10, padx=20)
        Label(marco_b, text=duelo.esgrimista_b.nombre, bg="#E8E2E2", width=25, anchor=W).pack(side=LEFT)
        Button(marco_b, text="Sanción leve", command=lambda: [duelo.registrar_falta_leve_b(), self.actualizar_broadcast_silencioso(cat), messagebox.showinfo("Sanción", "Leve registrada.", parent=vent)], bg="#2c3e50", fg="white").pack(side=LEFT, padx=5)
        Button(marco_b, text="Sanción Grave", command=lambda: [duelo.esgrimista_b.registrar_falta_grave(duelo_str=duelo_str), self.actualizar_broadcast_silencioso(cat), messagebox.showinfo("Sanción", "Grave registrada.", parent=vent)], bg="#940101", fg="white").pack(side=LEFT, padx=5)
    
    def abrir_tabla_posiciones(self, cat, ventana_padre):
        vent = Toplevel(ventana_padre)
        vent.title(f"Tabla de Posiciones - {cat.nombre}")
      ##  vent.geometry("600x500")
        vent.minsize(700,700)
        vent.transient(ventana_padre)
        
        arbol = ttk.Treeview(vent, columns=("Grupo", "Nombre", "Pts", "Dif"), show='headings')
        arbol.heading("Grupo", text="Grupo")
        arbol.heading("Nombre", text="Esgrimista")
        arbol.heading("Pts", text="Puntos")
        arbol.heading("Dif", text="Dif.")
        
        arbol.column("Grupo", width=80, anchor=CENTER)
        arbol.column("Nombre", width=200)
        arbol.column("Pts", width=60, anchor=CENTER)
        arbol.column("Dif", width=60, anchor=CENTER)
        
        arbol.tag_configure("encabezado_grupo", background="#940101", foreground="white")
        arbol.tag_configure("separador", background="#f4f6f7")
        arbol.tag_configure("clasificado", background="#d4efdf")
        
        clasificados = cat.obtener_clasificados()
        
        for grupo in cat.grupos:
            arbol.insert("", "end", values=(f"GRUPO {grupo.numero}", "", "", ""), tags=("encabezado_grupo",))
            for esg in grupo.posiciones():
                tag = "clasificado" if esg in clasificados else ""
                arbol.insert("", "end", values=("", esg.nombre, esg.puntos_totales, esg.diferencia_total), tags=(tag,))
            arbol.insert("", "end", values=("", "", "", ""), tags=("separador",))
                
        scrollbar = ttk.Scrollbar(vent, orient=VERTICAL, command=arbol.yview)
        arbol.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=RIGHT, fill=Y)
        arbol.pack(fill=BOTH, expand=True)

    def abrir_gestion_sanciones(self, cat, ventana_padre):
        vent = Toplevel(ventana_padre)
        vent.title(f"Gestión de Sanciones - {cat.nombre}")
      ##  vent.geometry("700x450")
        vent.minsize(700,450)
        vent.transient(ventana_padre)
        vent.grab_set()
        
        marco_lista = Frame(vent, bg="#E8E2E2")
        marco_lista.pack(fill=BOTH, expand=True, padx=20, pady=20)
        
        arbol = ttk.Treeview(marco_lista, columns=("Nombre", "Leves", "Graves"), show='headings')
        arbol.heading("Nombre", text="Nombre")
        arbol.heading("Leves", text="Faltas Leves")
        arbol.heading("Graves", text="Faltas Graves")
        
        arbol.column("Nombre", width=250)
        arbol.column("Leves", width=150, anchor=CENTER)
        arbol.column("Graves", width=150, anchor=CENTER)
        arbol.tag_configure("rojo_peligro", foreground="#940101")
        arbol.pack(fill=BOTH, expand=True)
        
        mapa_esgrimistas = {}
        
        def dibujar_lista():
            for item in arbol.get_children():
                arbol.delete(item)
            mapa_esgrimistas.clear()
            
            for esg in cat.esgrimistas:
                texto_leves = f"{esg.faltas_leves_totales} ({esg.derrotas_por_faltas})"
                texto_graves = f"{esg.faltas_graves_totales} E" if esg.faltas_graves_totales >= 2 else str(esg.faltas_graves_totales)
                tag = "rojo_peligro" if esg.descalificado else ""
                iid = arbol.insert("", "end", values=(esg.nombre, texto_leves, texto_graves), tags=(tag,))
                mapa_esgrimistas[iid] = esg
                
        dibujar_lista()
        
        def boton_editar_seleccionado():
            seleccion = arbol.selection()
            if not seleccion:
                messagebox.showwarning("Atención", "Seleccione a un esgrimista de la lista primero.")
                return
            esg_seleccionado = mapa_esgrimistas[seleccion[0]]
            self.ventana_vacia(f"Editar Historial: {esg_seleccionado.nombre}", vent)
            
        Button(vent, text="Editar Sanciones del Seleccionado", command=boton_editar_seleccionado, bg="#2c3e50", fg="white", font=("Georgia", 11, "bold")).pack(pady=10)

    def recalcular_sanciones_esgrimista(self, esg):
        esg.faltas_graves_totales = sum(1 for s in esg.historial_sanciones if s['tipo'] == 'Grave')
        esg.descalificado = (esg.faltas_graves_totales >= 2)
        
        esg.faltas_leves_totales = sum(1 for s in esg.historial_sanciones if s['tipo'] == 'Leve')
        
        conteo_por_duelo = {}
        for s in esg.historial_sanciones:
            if s['tipo'] == 'Leve' and s['duelo'] != "-- NINGUNO --":
                conteo_por_duelo[s['duelo']] = conteo_por_duelo.get(s['duelo'], 0) + 1
        
        esg.derrotas_por_faltas = sum(1 for count in conteo_por_duelo.values() if count >= 3)

    def editar_historial_sanciones(self, esg, ventana_padre, cat, callback_actualizar_padre):
        vent = Toplevel(ventana_padre)
        vent.title(f"Historial de Sanciones - {esg.nombre}")
       ## vent.geometry("700x400")
        vent.config(bg="#E8E2E2")
        vent.transient(ventana_padre)
        vent.grab_set()

        Label(vent, text=f"Sanciones de: {esg.nombre}", bg="#E8E2E2", font=("Georgia", 14, "bold")).pack(pady=10)

        arbol = ttk.Treeview(vent, columns=("Check", "Fase", "Duelo", "Sancion"), show='headings')
        arbol.heading("Check", text="[ ]")
        arbol.heading("Fase", text="Fase")
        arbol.heading("Duelo", text="Duelo")
        arbol.heading("Sancion", text="Sanción")
        
        arbol.column("Check", width=40, anchor=CENTER)
        arbol.column("Fase", width=120, anchor=CENTER)
        arbol.column("Duelo", width=350, anchor=W)
        arbol.column("Sancion", width=100, anchor=CENTER)
        
        arbol.tag_configure("leve", background="#f39c12", foreground="white") 
        arbol.tag_configure("grave", background="#940101", foreground="white")
        
        arbol.pack(fill=BOTH, expand=True, padx=20)

        def dibujar_historial():
            for item in arbol.get_children():
                arbol.delete(item)
            for i, sancion in enumerate(esg.historial_sanciones):
                tag = "grave" if sancion['tipo'] == 'Grave' else "leve"
                arbol.insert("", "end", iid=str(i), values=("[ ]", sancion['fase'], sancion['duelo'], sancion['tipo']), tags=(tag,))
            evaluar_boton_eliminar()

        def alternar_check(event):
            region = arbol.identify("region", event.x, event.y)
            if region == "cell":
                columna = arbol.identify_column(event.x)
                if columna == "#1": 
                    item = arbol.identify_row(event.y)
                    if item:
                        valores = list(arbol.item(item, "values"))
                        valores[0] = "[X]" if valores[0] == "[ ]" else "[ ]"
                        arbol.item(item, values=valores)
                        evaluar_boton_eliminar()

        arbol.bind("<ButtonRelease-1>", alternar_check)

        marco_botones = Frame(vent, bg="#E8E2E2")
        marco_botones.pack(fill=X, pady=15, padx=20)

        btn_eliminar = Button(marco_botones, text="Eliminar Seleccionadas", bg="#2c3e50", fg="white", font=("Georgia", 10, "bold"), state=DISABLED)
        btn_eliminar.pack(side=LEFT)
        
        def evaluar_boton_eliminar():
            marcados = [item for item in arbol.get_children() if arbol.item(item, "values")[0] == "[X]"]
            btn_eliminar.config(state=NORMAL if marcados else DISABLED)

        def ejecutar_eliminacion():
            marcados = [int(item) for item in arbol.get_children() if arbol.item(item, "values")[0] == "[X]"]
            marcados.sort(reverse=True)
            for indice in marcados:
                esg.historial_sanciones.pop(indice)
            
            self.recalcular_sanciones_esgrimista(esg)
            dibujar_historial()
            callback_actualizar_padre()

        btn_eliminar.config(command=ejecutar_eliminacion)

        Button(marco_botones, text="Agregar Sanción", command=lambda: self.agregar_sancion_manual(esg, cat, vent, dibujar_historial, callback_actualizar_padre), bg="#2c3e50", fg="white", font=("Georgia", 10, "bold")).pack(side=RIGHT)

        dibujar_historial()

    def agregar_sancion_manual(self, esg, cat, ventana_padre, callback_historial, callback_padre):
        vent = Toplevel(ventana_padre)
        vent.title("Agregar Sanción Manual")
        vent.geometry("450x250")
      ##  vent.config(bg="#E8E2E2")
        vent.transient(ventana_padre)
        vent.grab_set()

        Label(vent, text="Fase:", bg="#E8E2E2", font=("Georgia", 10, "bold")).grid(row=0, column=0, pady=15, padx=20, sticky=W)
        combo_fase = ttk.Combobox(vent, values=["Grupos", "Eliminatorias"], state="readonly", width=30)
        combo_fase.grid(row=0, column=1)
        combo_fase.current(0)

        Label(vent, text="Duelo:", bg="#E8E2E2", font=("Georgia", 10, "bold")).grid(row=1, column=0, pady=5, padx=20, sticky=W)
        
        lista_duelos = ["-- NINGUNO --"]
        for grupo in cat.grupos:
            for duelo in grupo.duelos:
                if duelo.esgrimista_a == esg or duelo.esgrimista_b == esg:
                    lista_duelos.append(f"{duelo.esgrimista_a.nombre} vs {duelo.esgrimista_b.nombre}")
                    
        combo_duelo = ttk.Combobox(vent, values=lista_duelos, state="readonly", width=30)
        combo_duelo.grid(row=1, column=1)
        combo_duelo.current(0)

        Label(vent, text="Tipo Sanción:", bg="#E8E2E2", font=("Georgia", 10, "bold")).grid(row=2, column=0, pady=15, padx=20, sticky=W)
        combo_tipo = ttk.Combobox(vent, values=["Leve", "Grave"], state="readonly", width=30)
        combo_tipo.grid(row=2, column=1)
        combo_tipo.current(0)

        def guardar_manual():
            esg.historial_sanciones.append({
                "fase": combo_fase.get(),
                "duelo": combo_duelo.get(),
                "tipo": combo_tipo.get()
            })
            self.recalcular_sanciones_esgrimista(esg)
            callback_historial()
            callback_padre()
            vent.destroy()

        Button(vent, text="Guardar Sanción", command=guardar_manual, bg="#940101", fg="white", font=("Georgia", 11, "bold")).grid(row=3, column=0, columnspan=2, pady=20)


    def explorar_fixture_ete3(self, cat, ventana_padre):
        import math
        
        clasificados_set = cat.obtener_clasificados()
        n_clasificados = len(clasificados_set)
        
        if n_clasificados < 2:
            messagebox.showwarning("Atención", "No hay suficientes clasificados (mínimo 2) para armar un fixture.", parent=ventana_padre)
            return
            
        clasificados_ordenados = sorted(
            list(clasificados_set), 
            key=lambda e: (e.puntos_totales, e.diferencia_total), 
            reverse=True
        )
        
        n_rondas = math.ceil(math.log2(n_clasificados))
        n_slots = 2 ** n_rondas
        
        nombres_jugadores = [e.nombre for e in clasificados_ordenados]
        while len(nombres_jugadores) < n_slots:
            nombres_jugadores.append("BYE (Pasa Libre)")
            
        def generar_orden_bracket(n):
            if n == 1:
                return [1]
            mitad = generar_orden_bracket(n // 2)
            nueva = []
            for semilla in mitad:
                nueva.append(semilla)
                nueva.append(n + 1 - semilla)
            return nueva
            
        orden_semillas = generar_orden_bracket(n_slots)
        nombres_ordenados = [nombres_jugadores[i - 1] for i in orden_semillas]
        
        def construir_newick_con_nombres(lista_nombres, ronda_actual):
            if len(lista_nombres) == 1:
                return lista_nombres[0].replace(" ", "_").replace("(", "").replace(")", "")
                
            mitad = len(lista_nombres) // 2
            izq = construir_newick_con_nombres(lista_nombres[:mitad], ronda_actual + 1)
            der = construir_newick_con_nombres(lista_nombres[mitad:], ronda_actual + 1)
            
            if ronda_actual == 1:
                nombre_nodo = "FINAL"
            elif ronda_actual == 2:
                nombre_nodo = "Semis"
            elif ronda_actual == 3:
                nombre_nodo = "Cuartos"
            elif ronda_actual == 4:
                nombre_nodo = "Octavos"
            else:
                nombre_nodo = f"Ronda_{ronda_actual}"
                
            return f"({izq},{der}){nombre_nodo}"
            
        newick_final = construir_newick_con_nombres(nombres_ordenados, 1) + ";"
        
        try:
            arbol_final = et.Tree(newick_final, format=1)
            arbol_bronce = et.Tree("(Perdedor_Semi_1, Perdedor_Semi_2)Bronce;", format=1)
            
            for nodo in arbol_final.traverse():
                nodo.name = nodo.name.replace("_", " ")
            for nodo in arbol_bronce.traverse():
                nodo.name = nodo.name.replace("_", " ")
            
            vent = Toplevel(ventana_padre)
            vent.title("Explorador Estructural ETE3 - Cuadro de Eliminatorias")
            vent.geometry("750x650")
            vent.config(bg="#E8E2E2")
            
            Label(vent, text=f"Árbol de Eliminatorias (Llave de {n_slots})", font=("Georgia", 14, "bold"), bg="#E8E2E2").pack(pady=10)
            
            texto = Text(vent, bg="#2c3e50", fg="white", font=("Courier", 10))
            texto.pack(fill=BOTH, expand=True, padx=20, pady=10)
            texto.insert(END, "--- LLAVE POR EL ORO (CUADRO PRINCIPAL) ---\n\n")
            texto.insert(END, arbol_final.get_ascii(show_internal=True) + "\n\n")
            texto.insert(END, "--- LLAVE POR EL BRONCE ---\n\n")
            texto.insert(END, arbol_bronce.get_ascii(show_internal=True) + "\n")
            texto.config(state=DISABLED)
            
            def lanzar_visor():
                try:
                    arbol_final.show()
                except Exception as e:
                    messagebox.showerror("Error Visor", f"No se pudo iniciar el renderizado Qt.\n{str(e)}", parent=vent)
            
            Button(vent, text="Lanzar Gráfico Interactivo ETE3", command=lanzar_visor, bg="#940101", fg="white", font=("Georgia", 11, "bold")).pack(pady=15)
            
        except Exception as e:
            messagebox.showerror("Error ETE3", f"Error al generar el árbol:\n{str(e)}", parent=ventana_padre)

    def abrir_duelos_eliminatorios(self, cat, ventana_padre):
        import math
        
        vent = Toplevel(ventana_padre)
        vent.title(f"Duelos Eliminatorios - {cat.nombre}")
        vent.geometry("1100x700")
        vent.minsize(1100,700) 
        vent.config(bg="#E8E2E2")
        vent.transient(ventana_padre)
        vent.grab_set()

        canvas = Canvas(vent, bg="#E8E2E2", highlightthickness=0)
        scrollbar = ttk.Scrollbar(vent, orient=VERTICAL, command=canvas.yview)
        marco_scroll = Frame(canvas, bg="#E8E2E2")
        
        marco_scroll.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=marco_scroll, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=LEFT, fill=BOTH, expand=True, padx=20, pady=20)
        scrollbar.pack(side=RIGHT, fill=Y)

        clasificados_set = cat.obtener_clasificados()
        n_clasificados = len(clasificados_set)
        
        if n_clasificados < 2:
            Label(marco_scroll, text="No hay suficientes clasificados.", font=("Georgia", 12), bg="#E8E2E2").pack()
            return
            
        clasificados_ordenados = sorted(list(clasificados_set), key=lambda e: (e.puntos_totales, e.diferencia_total), reverse=True)
        n_rondas = math.ceil(math.log2(n_clasificados))
        n_slots = 2 ** n_rondas
        
        nombres_jugadores = [e.nombre for e in clasificados_ordenados]
        while len(nombres_jugadores) < n_slots:
            nombres_jugadores.append("BYE (Pasa Libre)")
            
        def generar_orden_bracket(n):
            if n == 1: return [1]
            mitad = generar_orden_bracket(n // 2)
            nueva = []
            for semilla in mitad:
                nueva.append(semilla)
                nueva.append(n + 1 - semilla)
            return nueva
            
        orden_semillas = generar_orden_bracket(n_slots)
        nombres_ordenados = [nombres_jugadores[i - 1] for i in orden_semillas]

        duelos_por_fase = {}
        
        duelos_fase_1 = []
        for i in range(0, n_slots, 2):
            duelos_fase_1.append((nombres_ordenados[i], nombres_ordenados[i+1]))
        duelos_por_fase[n_rondas] = duelos_fase_1

        for ronda in range(n_rondas - 1, 0, -1):
            duelos_fase_n = []
            n_duelos_ronda_anterior = len(duelos_por_fase[ronda + 1])
            for i in range(1, n_duelos_ronda_anterior, 2):
                duelos_fase_n.append((f"Ganador Llave {i}", f"Ganador Llave {i+1}"))
            duelos_por_fase[ronda] = duelos_fase_n

        for ronda in range(n_rondas, 0, -1):
            if ronda == 1:
                nombre_fase = "FINAL"
            elif ronda == 2:
                nombre_fase = "SEMIFINALES"
            elif ronda == 3:
                nombre_fase = "CUARTOS DE FINAL"
            elif ronda == 4:
                nombre_fase = "OCTAVOS DE FINAL"
            else:
                nombre_fase = f"RONDA DE {2**ronda}"
                
            Label(marco_scroll, text=nombre_fase, font=("Georgia", 16, "bold"), bg="#E8E2E2", fg="#2c3e50").pack(pady=(25, 10), anchor=W)
            
            lista_duelos = duelos_por_fase[ronda]
            for i, (esg_a, esg_b) in enumerate(lista_duelos, 1):
                fila = Frame(marco_scroll, bg="#E8E2E2")
                fila.pack(fill=X, pady=6)
                
                llave_id = "ORO" if nombre_fase == "FINAL" else f"Llave {i}" 
                
                texto_duelo = f"[{llave_id}]   {esg_a}   -  vs  -   {esg_b}"
                Label(fila, text=texto_duelo, bg="#E8E2E2", font=("Georgia", 11), width=50, anchor=W).pack(side=LEFT)
                
                Button(fila, text="Ingresar|Modificar Resultado", 
                       command=lambda r=ronda, num=i, a=esg_a, b=esg_b: self.abrir_resultado_eliminatoria(cat, r, num, a, b, vent), 
                       bg="#2c3e50", fg="white").pack(side=LEFT, padx=(10, 5))
                
                Button(fila, text="Registrar Sanciones", 
                       command=lambda r=ronda, num=i, a=esg_a, b=esg_b: self.abrir_sanciones_eliminatoria(cat, r, num, a, b, vent), 
                       bg="#940101", fg="white").pack(side=LEFT, padx=5)
            
            if nombre_fase == "SEMIFINALES":
                Label(marco_scroll, text="TERCER LUGAR", font=("Georgia", 16, "bold"), bg="#E8E2E2", fg="#940101").pack(pady=(25, 10), anchor=W)
                fila = Frame(marco_scroll, bg="#E8E2E2")
                fila.pack(fill=X, pady=6)
                texto_duelo = f"[BRONCE]   Perdedor Llave 1   -  vs  -   Perdedor Llave 2"
                Label(fila, text=texto_duelo, bg="#E8E2E2", font=("Georgia", 11), width=50, anchor=W).pack(side=LEFT)
                Button(fila, text="Ingresar|Modificar Resultado", 
                       command=lambda: self.abrir_resultado_eliminatoria(cat, "BRONCE", 1, "Perdedor Llave 1", "Perdedor Llave 2", vent), 
                       bg="#2c3e50", fg="white").pack(side=LEFT, padx=(10, 5))
                Button(fila, text="Registrar Sanciones", 
                        command=lambda: self.abrir_sanciones_eliminatoria(cat, "BRONCE", 1, "Perdedor Llave 1", "Perdedor Llave 2", vent), 
                        bg="#940101", fg="white").pack(side=LEFT, padx=5)
        marco_botones = Frame(vent, bg="#E8E2E2")
        marco_botones.pack(fill=X, side=BOTTOM, pady=20, padx=30)
        Button(marco_botones, text="Guardar", command=self.exportar_configuracion, bg="#2c3e50", fg="white", font=("Georgia", 11, "bold")).pack(side=LEFT)
        Button(marco_botones, text="Cerrar", command=vent.destroy, bg="#2c3e50", fg="white", font=("Georgia", 11, "bold")).pack(side=RIGHT)

    def abrir_resultado_eliminatoria(self, cat, ronda, num_llave, esg_a, esg_b, ventana_padre):
        vent = Toplevel(ventana_padre)
        vent.title(f"Resultado - {esg_a} vs {esg_b}")
        vent.geometry("450x300")
        vent.minsize(600,350)
        vent.config(bg="#E8E2E2")
        vent.transient(ventana_padre)
        vent.grab_set()

        Label(vent, text=f"Fase: {ronda} - Llave {num_llave}", font=("Georgia", 14, "bold"), bg="#E8E2E2", fg="#2c3e50").pack(pady=15)
        
        marco_inputs = Frame(vent, bg="#E8E2E2")
        marco_inputs.pack(fill=X, padx=20, pady=10)

        Label(marco_inputs, text=esg_a, font=("Georgia", 12), bg="#E8E2E2", width=20, anchor=E).grid(row=0, column=0, pady=10, padx=5)
        pts_a = IntVar()
        Entry(marco_inputs, textvariable=pts_a, width=5, font=("Georgia", 12)).grid(row=0, column=1, pady=10)

        Label(marco_inputs, text=esg_b, font=("Georgia", 12), bg="#E8E2E2", width=20, anchor=E).grid(row=1, column=0, pady=10, padx=5)
        pts_b = IntVar()
        Entry(marco_inputs, textvariable=pts_b, width=5, font=("Georgia", 12)).grid(row=1, column=1, pady=10)

        def guardar():
            self.actualizar_broadcast_silencioso(cat)
            vent.destroy()

        Button(vent, text="Guardar Resultado", command=guardar, bg="#2c3e50", fg="white", font=("Georgia", 11, "bold")).pack(pady=20)

    def abrir_sanciones_eliminatoria(self, cat, ronda, num_llave, esg_a, esg_b, ventana_padre):
        vent = Toplevel(ventana_padre)
        vent.title(f"Sanciones - {esg_a} vs {esg_b}")
        vent.geometry("400x250")
        vent.config(bg="#E8E2E2")
        vent.transient(ventana_padre)
        vent.grab_set()

        Label(vent, text=f"Sanciones: Llave {num_llave}", font=("Georgia", 14, "bold"), bg="#E8E2E2", fg="#940101").pack(pady=15)

        def registrar_falta(esgrimista):
            self.actualizar_broadcast_silencioso(cat)
            vent.destroy()

        Button(vent, text=f"Falta Leve: {esg_a}", command=lambda: registrar_falta(esg_a), bg="#e67e22", fg="white", font=("Georgia", 11, "bold"), width=30).pack(pady=10)
        Button(vent, text=f"Falta Leve: {esg_b}", command=lambda: registrar_falta(esg_b), bg="#e67e22", fg="white", font=("Georgia", 11, "bold"), width=30).pack(pady=10)

    def ejecutar_broadcast(self, cat, etapa, label_status):
        self.broadcast_activo = True
        self.etapa_broadcast = etapa
        self.label_status_web = label_status
        
        label_status.config(text="Actualizando...", fg="#d35400") 
        
        def tarea_git():
            try:
                ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                INDEX_PATH = os.path.join(ROOT_DIR, "index.html")
                
                html_content = cat.generar_index_html(etapa)
                with open(INDEX_PATH, "w", encoding="utf-8") as f:
                    f.write(html_content)
                    
                subprocess.run(["git", "add", "index.html"], cwd=ROOT_DIR, check=True, capture_output=True)
                subprocess.run(["git", "commit", "-m", f"Broadcast {etapa} en vivo - {cat.nombre}"], cwd=ROOT_DIR, check=False, capture_output=True) 
                subprocess.run(["git", "push", "-u", "origin", "master:main"], cwd=ROOT_DIR, check=True, capture_output=True)
                label_status.config(text="En línea", fg="#27ae60")
            except Exception as e:
                label_status.config(text="Error de conexión", fg="#940101")
                print(f"Error en Broadcast Git: {str(e)}")
                
        import threading
        threading.Thread(target=tarea_git, daemon=True).start()

    def detener_broadcast(self, label_status):
        self.broadcast_activo = False
        label_status.config(text="Apagando...", fg="#d35400")
        
        def tarea_git():
            try:
                ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                INDEX_PATH = os.path.join(ROOT_DIR, "index.html")
                
                html_standby = """<!DOCTYPE html>
                <html lang="es"><head><meta charset="utf-8"><title>Standby - HEMA Chile</title>
                <style>
                    body { font-family: Georgia, serif; text-align: center; padding-top: 15vh; background-color: #f4f6f7; margin: 0; }
                    .contenedor { background-color: white; padding: 40px; border-radius: 10px; display: inline-block; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
                </style></head>
                <body>
                <div class="contenedor">
                    <img src="./assets/images/hema_chile_logo.png" onerror="this.onerror=null; this.src='./assets/icons/logo_hemachile.ico';" alt="Logo" width="120">
                    <h1 style="color: #940101;">Torneo de Novatos HEMA Chile 2026</h1>
                    <h2 style="color: #2c3e50;">Transmisión en espera.</h2>
                    <p style="color: #7f8c8d; font-size: 18px;">El torneo ha finalizado esta etapa o se encuentra en pausa.<br>En breve iniciaremos la siguiente transmisión.</p>
                </div>
                </body></html>"""
                
                with open(INDEX_PATH, "w", encoding="utf-8") as f:
                    f.write(html_standby)
                
                subprocess.run(["git", "add", "index.html"], cwd=ROOT_DIR, check=True, capture_output=True)
                subprocess.run(["git", "commit", "-m", "Fin de Broadcast (Standby)"], cwd=ROOT_DIR, check=False, capture_output=True)
                subprocess.run(["git", "push", "-u", "origin", "master:main"], cwd=ROOT_DIR, check=True, capture_output=True)
                
                label_status.config(text="Apagado", fg="#7f8c8d") 
            except Exception as e:
                label_status.config(text="Error", fg="#940101")
                print(f"Error en Broadcast Git: {str(e)}")

        import threading
        threading.Thread(target=tarea_git, daemon=True).start()

    def actualizar_broadcast_silencioso(self, cat):
        if not getattr(self, 'broadcast_activo', False):
            return
            
        def tarea_git():
            try:
                ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                INDEX_PATH = os.path.join(ROOT_DIR, "index.html")
                
                html_content = cat.generar_index_html(self.etapa_broadcast)
                with open(INDEX_PATH, "w", encoding="utf-8") as f:
                    f.write(html_content)
                    
                subprocess.run(["git", "add", "index.html"], cwd=ROOT_DIR, check=True, capture_output=True)
                subprocess.run(["git", "commit", "-m", "Auto-actualización de puntaje en vivo"], cwd=ROOT_DIR, check=False, capture_output=True)
                subprocess.run(["git", "push", "-u", "origin", "master:main"], cwd=ROOT_DIR, check=True, capture_output=True)
            except Exception as e:
                print(f"Error en autoguardado Git: {str(e)}")
                if hasattr(self, 'label_status_web'):
                    self.label_status_web.config(text="Error de Sincr.", fg="#940101")
                    
        import threading
        threading.Thread(target=tarea_git, daemon=True).start()
 

#### comentario de prueba


if __name__ == "__main__":
    pagina_principal = Tk()
    app = PantallaCarga(pagina_principal)
    pagina_principal.mainloop()