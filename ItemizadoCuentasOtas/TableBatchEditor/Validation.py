class ToolValidator:
  # Class to add custom behavior and properties to the tool and tool parameters.

    def __init__(self):
        # Set self.params for use in other validation methods.
        self.params = arcpy.GetParameterInfo()
        self.campo_anterior = None

    def initializeParameters(self):
        # Customize parameter properties. This method gets called when the
        # tool is opened.
        return

    def updateParameters(self):
        # Modify the values and properties of parameters before internal
        # validation is performed.
        tabla = self.params[0].value
        campo_alias = self.params[1].valueAsText
        
        if not tabla:
            return

        desc = arcpy.Describe(tabla)

        # -------------------------
        # 1 Construir diccionario alias -> name
        # -------------------------
        alias_dict = {}
        alias_list = []

        for f in desc.fields:
            if not f.required:  # evitar OBJECTID, Shape, etc.
                alias_list.append(f.aliasName)
                alias_dict[f.aliasName] = f.name

        # Cargar lista de alias en parametro 2

        self.params[1].filter.list = alias_list

        # Si el campo fue modificado por el usuario, limpiar nuevo valor
        # Detectar cambio real de campo
        if self.params[1].altered and not self.params[1].hasBeenValidated:
            self.params[2].value = None

        if not campo_alias:
            return

        campo_real = alias_dict.get(campo_alias)

        if not campo_real:
            return

        # Buscar objeto campo real
        campo_obj = None
        for f in desc.fields:
            if f.name == campo_real:
                campo_obj = f
                break

        if not campo_obj:
            return

        # -------------------------
        # 2 Manejar dominio
        # -------------------------
        if campo_obj.domain:

            dominios = arcpy.da.ListDomains(desc.path)

            for dom in dominios:
                if dom.name == campo_obj.domain:
                    if dom.domainType == "CodedValue":

                        coded_dict = dom.codedValues

                        # Mostrar DESCRIPCIONES
                        descripciones = list(coded_dict.values())
                        self.params[2].filter.list = descripciones

                        valor_actual = self.params[2].valueAsText

                        # Solo asignar si no hay valor válido
                        if not valor_actual or valor_actual not in descripciones:
                            if descripciones:
                                self.params[2].value = descripciones[0]

                    break

        else:
            self.params[2].filter.list = []

        return

    def updateMessages(self):
        # Modify the messages created by internal validation for each tool
        # parameter. This method is called after internal validation.
        return

    # def isLicensed(self):
    #     # Set whether the tool is licensed to execute.
    #     return True

    # def postExecute(self):
    #     # This method takes place after outputs are processed and
    #     # added to the display.
    #     return
