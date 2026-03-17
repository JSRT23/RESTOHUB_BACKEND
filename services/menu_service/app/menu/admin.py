from django.contrib import admin
# super user admin: menu_admin Menu12345*
from .models import Restaurante, Categoria, Plato, Ingrediente, PlatoIngrediente

admin.site.register(Restaurante)
admin.site.register(Categoria)
admin.site.register(Plato)
