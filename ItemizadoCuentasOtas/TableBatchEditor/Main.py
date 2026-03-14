# import arcpy 

# tabla = arcpy.GetParameter(0)
# #objectids_str = arcpy.GetParameterAsText(1)
# campo = arcpy.GetParameterAsText(1)
# nuevo_valor = arcpy.GetParameterAsText(2)

# # desc = arcpy.Describe(tabla)
# # fidset = desc.FIDSet
# # # if not objectids_str:
# # #     arcpy.AddError("No se recibieron OBJECTIDs.")
# # #     raise Exception("Sin registros seleccionados.")

# # if not fidset:
# #     arcpy.AddError("Debe seleccionar al menos un registro de la tabla")
# #     raise Exception("No hay selección.")

# # objectids = fidset.split(";")


# # -------------------------------------------------
# # 1 Alias -> nombre real de campo
# # -------------------------------------------------
# fields = arcpy.ListFields(tabla)
# alias_dict = {f.aliasName: f.name for f in fields}
# campo = alias_dict.get(campo, campo)

# # -------------------------------------------------
# # 2 Convertir descripcion dominio -> clave real
# # -------------------------------------------------
# campo_obj = next((f for f in fields if f.name == campo), None)

# if campo_obj and campo_obj.domain:

#     dominios = arcpy.da.ListDomains(desc.path)

#     for dom in dominios:
#         if dom.name == campo_obj.domain and dom.domainType == "CodedValue":

#             # descripcion -> clave
#             desc_to_code = {v: k for k, v in dom.codedValues.items()}
#             nuevo_valor = desc_to_code.get(nuevo_valor, nuevo_valor)

#             break

# # -------------------------------------------------
# # 3 Detectar tipo y convertir
# # -------------------------------------------------
# if campo_obj:

#     tipo = campo_obj.type

#     try:
#         if tipo in ["Double", "Single"]:
#             nuevo_valor = nuevo_valor.replace(",", ".")
#             nuevo_valor = float(nuevo_valor)

#         elif tipo in ["Integer", "SmallInteger"]:
#             nuevo_valor = int(nuevo_valor)

#         elif tipo == "String":
#             nuevo_valor = str(nuevo_valor)

#     except:
#         arcpy.AddError("El valor ingresado no es compatible con el tipo del campo.")
#         raise

# # -------------------------------------------------
# # 4 Advertencia si no pertenece al dominio
# # -------------------------------------------------
# if campo_obj and campo_obj.domain:

#     dominio_nombre = campo_obj.domain
#     dominios = arcpy.da.ListDomains(desc.path)

#     for dom in dominios:
#         if dom.name == dominio_nombre:
#             if dom.domainType == "CodedValue":
#                 if nuevo_valor not in dom.codedValues.keys():
#                     arcpy.AddWarning("El valor no pertenece al dominio del campo.")
#             break

# # -------------------------------------------------
# # 5 Update
# # -------------------------------------------------

# # objectids = [oid.strip() for oid in objectids_str.split(",")]
# # oid_field = arcpy.Describe(tabla).OIDFieldName
# # where_clause = f"{oid_field} IN ({','.join(objectids)})"

# # arcpy.AddMessage(f"Actualizando {len(objectids)} registros...")
# #rcpy.AddMessage(f"Actualizando {len(tabla)} registros...")
# arcpy.AddMessage(f"Campo: {campo}")
# arcpy.AddMessage(f"Nuevo valor: {nuevo_valor}")

# count = 0
# with arcpy.da.UpdateCursor(tabla, [campo]) as cursor:
#     for row in cursor:
#         row[0] = nuevo_valor
#         cursor.updateRow(row)
#         count += 1

# arcpy.AddMessage(f"Registros actualizados: {count}")

#######################################################################################################
import arcpy 

tabla = arcpy.GetParameter(0)
campo = arcpy.GetParameterAsText(1)
nuevo_valor = arcpy.GetParameterAsText(2)

fields = arcpy.ListFields(tabla)

# Alias -> nombre real
alias_dict = {f.aliasName: f.name for f in fields}
campo = alias_dict.get(campo, campo)

campo_obj = next((f for f in fields if f.name == campo), None)

if not campo_obj:
    arcpy.AddError("Campo no encontrado.")
    raise Exception("Campo inválido.")

# Detectar tipo y convertir
tipo = campo_obj.type

try:
    if tipo in ["Double", "Single"]:
        nuevo_valor = nuevo_valor.replace(",", ".")
        nuevo_valor = float(nuevo_valor)

    elif tipo in ["Integer", "SmallInteger"]:
        nuevo_valor = int(nuevo_valor)

    elif tipo == "String":
        nuevo_valor = str(nuevo_valor)

except:
    arcpy.AddError("El valor ingresado no es compatible con el tipo del campo.")
    raise

arcpy.AddMessage(f"Campo: {campo}")
arcpy.AddMessage(f"Nuevo valor: {nuevo_valor}")

count = 0
with arcpy.da.UpdateCursor(tabla, [campo]) as cursor:
    for row in cursor:
        row[0] = nuevo_valor
        cursor.updateRow(row)
        count += 1

arcpy.AddMessage(f"Registros actualizados: {count}")