import uuid
from django.db import models


class Restaurante(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    nombre = models.CharField(max_length=255)
    pais = models.CharField(max_length=100)
    ciudad = models.CharField(max_length=100)
    direccion = models.TextField()

    moneda = models.CharField(max_length=10)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre


class Categoria(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return self.nombre


class Plato(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    nombre = models.CharField(max_length=255)
    descripcion = models.TextField()

    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    imagen = models.URLField(blank=True, null=True)
    activo = models.BooleanField(default=True)

    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
        null=True,
        blank=True
    )

    def __str__(self):
        return self.nombre


class Ingrediente(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    nombre = models.CharField(max_length=255)
    unidad_medida = models.CharField(max_length=50)
    descripcion = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nombre


class PlatoIngrediente(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    plato = models.ForeignKey(
        Plato, on_delete=models.CASCADE, related_name="ingredientes")
    ingrediente = models.ForeignKey(Ingrediente, on_delete=models.CASCADE)

    cantidad = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.plato.nombre} - {self.ingrediente.nombre}"


class PrecioPlato(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    plato = models.ForeignKey(
        Plato, on_delete=models.CASCADE, related_name="precios")
    restaurante = models.ForeignKey(Restaurante, on_delete=models.CASCADE)

    precio = models.DecimalField(max_digits=10, decimal_places=2)

    fecha_inicio = models.DateTimeField()
    fecha_fin = models.DateTimeField(blank=True, null=True)

    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.plato.nombre} - {self.restaurante.nombre} - {self.precio}"
