import arcpy
import os

class ToolValidator:
    def __init__(self):
        self.params = arcpy.GetParameterInfo()

    def initializeParameters(self):
        # El parámetro de usuario asignado se actualiza cuando se carga el tool
        return

    def updateParameters(self):
        # Cambia la lista de valores del parámetro usuario asignado externo
        # en base al dominio configurado en el campo de la tabla OTs.

        ots_relevadas = self.params[5].value
        if not ots_relevadas:
            self.params[4].filter.list = []
            return

        try:
            desc = arcpy.Describe(ots_relevadas)
        except Exception:
            self.params[4].filter.list = []
            return

        # obtener workspace de la capa / tabla, no la ruta completa del dataset
        workspace = getattr(desc, 'workspacePath', None) or getattr(desc, 'path', None) or ''
        if not workspace:
            workspace = os.path.dirname(desc.catalogPath) if getattr(desc, 'catalogPath', None) else ''

        # Buscamos el campo especificado, tolerando mayúsculas/minúsculas y alias.
        campo_obj = None
        field_name_candidates = ["USUARIO_ASIGNADO_EXTERNO", "usuario_asignado_externo"]

        for f in desc.fields:
            if f.name.upper() in [fn.upper() for fn in field_name_candidates] or \
               (f.aliasName and f.aliasName.upper() in [fn.upper() for fn in field_name_candidates]):
                campo_obj = f
                break

        if not campo_obj:
            self.params[4].filter.list = []
            return

        # Intentamos primero con dominio si está accesible
        value_list = []

        # Si el campo tiene dominio en la descripción de la capa
        if hasattr(campo_obj, 'domain') and campo_obj.domain:
            domain_info = campo_obj.domain
            if hasattr(domain_info, 'codedValues'):
                value_list = ["<TODOS>"] + list(domain_info.codedValues.values())

        # Si no tenemos dominio de campo, listamos valores activos en la tabla (servicio)
        if not value_list:
            usuario_vals = set()
            try:
                with arcpy.da.SearchCursor(ots_relevadas, [campo_obj.name]) as c:
                    for row in c:
                        if row[0] is not None:
                            usuario_vals.add(str(row[0]).strip())
            except Exception as e:
                arcpy.AddWarning(f"No se pudo obtener valores de campo desde OTs_Relevadas: {e}")

            if usuario_vals:
                value_list = ["<TODOS>"] + sorted(usuario_vals)

        self.params[4].filter.list = value_list


        # Si no hay valor aún, asignar <TODOS>
        if value_list and (not self.params[4].valueAsText):
            self.params[4].value = "<TODOS>"

    def updateMessages(self):
        # ningún mensaje especial por ahora
        return
