from django.db import models
import os
from django.utils import timezone

class Unites(models.Model):
    nom = models.CharField(max_length=20, verbose_name="Nom", unique=True)

    class Meta:
        ordering = ('nom', )
        verbose_name = "Unité"
        verbose_name_plural = "Unités"
    
    def __str__(self):
        return self.nom

    def __str__(self):
        return self.nom

class Categories(models.Model):
    nom = models.CharField(max_length=50, verbose_name="Nom", unique=True)
    image = models.FileField(upload_to="categories_images/", blank=True, null=True, verbose_name="Illustration")

    class Meta:
        ordering = ('nom', )
        verbose_name = "Catégorie"
        verbose_name_plural = "Catégories"

    def __str__(self):
        return self.nom


class Produits(models.Model):
    nom_produit = models.CharField(max_length=50, verbose_name="Nom")
    description = models.CharField(max_length=200, verbose_name="Description")
    quantite = models.IntegerField(verbose_name="Quantité", default=0)
    prix = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Prix")
    categorie = models.ForeignKey("Categories", on_delete=models.PROTECT, verbose_name="Catégorie")
    unite_de_vente = models.ForeignKey("Unites", on_delete=models.CASCADE, verbose_name="Unité de vente")

    class Meta:
        ordering = ('nom_produit', 'prix', )
        verbose_name = "Produit"
        verbose_name_plural = "Produits"

    def __str__(self):
        return self.nom_produit

    def get_image_principale(self):
        img = self.images.filter(ordre=1).first()
        return img.image.url if img else None


    def get_active_promotion(self):
        promo_produits = PromotionsProduits.objects.filter(produit=self)
        meilleure_promo = None
        meilleur_prix = self.prix

        for promo_prod in promo_produits:
            if promo_prod.promotion.is_active():
                prix_reduit = promo_prod.get_discounted_price(self.prix)
                if prix_reduit < meilleur_prix:
                    meilleur_prix = prix_reduit
                    meilleure_promo = promo_prod

        return meilleure_promo

    def get_discounted_price(self):
        promo_prod = self.get_active_promotion()
        if promo_prod:
            return round(promo_prod.get_discounted_price(self.prix), 2)
        return round(self.prix, 2)



class Images(models.Model):
    produit = models.ForeignKey("Produits", related_name="images", on_delete=models.CASCADE, verbose_name="Produit")
    image = models.ImageField(upload_to="produits_images/", verbose_name="Image", null=True)
    ordre = models.IntegerField(verbose_name="Ordre", default=1)
    principale = models.BooleanField(default=False, verbose_name="Image principale")

    class Meta:
        ordering = ('ordre', )
        verbose_name = "Image"
        verbose_name_plural = "Images"

    def __str__(self):
        return f"{self.produit.nom_produit} ({'Principale' if self.principale else 'Secondaire'})"

class Promotions(models.Model):
    nom = models.CharField(max_length=50, verbose_name="Nom")
    date_debut = models.DateField(verbose_name="Date de début")
    date_fin = models.DateField(verbose_name="Date de fin", null=True, blank=True)
    description = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        ordering = ['-date_debut']
        verbose_name = "Promotion"
        verbose_name_plural = "Promotions"

    def __str__(self):
        return self.nom

    def is_active(self):
        today = timezone.now().date()
        return self.date_debut <= today <= self.date_fin

class PromotionsProduits(models.Model):
    TYPE_CHOICES = [
        ('POURCENTAGE', 'Pourcentage'),
        ('MONTANT', 'Montant fixe'),
    ]

    produit = models.ForeignKey(Produits, on_delete=models.CASCADE)
    promotion = models.ForeignKey(Promotions, on_delete=models.CASCADE)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, verbose_name="Type de promotion")
    valeur_promo = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valeur de la promotion")

    class Meta:
        verbose_name = "Promotion sur produit"
        verbose_name_plural = "Promotions sur produits"

    def __str__(self):
        return f"{self.produit.nom_produit} - {self.promotion.nom} ({self.type}: {self.valeur_promo})"

    def get_discounted_price(self, prix_regulier):
        if self.type == "POURCENTAGE":
            reduction = prix_regulier * (self.valeur_promo / 100)
            return prix_regulier - reduction

        elif self.type == "MONTANT":
            return max(prix_regulier - self.valeur_promo, 0)

        return prix_regulier

class Adresses(models.Model):
    pays = models.CharField(max_length=50, verbose_name="Pays")
    ville = models.CharField(max_length=50, verbose_name="Ville")
    rue = models.CharField(max_length=100, verbose_name="Rue")
    numero = models.CharField(max_length=10, verbose_name="Numéro")
    boite = models.CharField(max_length=20, verbose_name="Boîte Postale", null=True, blank=True)
    code_postal = models.CharField(max_length=20, verbose_name="Code Postal")
    province = models.CharField(max_length=50, verbose_name="Province")
    

    class Meta:
        ordering = ('pays', 'ville', 'province', )
        verbose_name = "Adresse"
        verbose_name_plural = "Adresses"
    def __str__(self):
        return f"{self.numero} {self.rue}, {self.ville}, {self.province}, {self.pays}, {self.code_postal}"

class Clients(models.Model):
    adresse = models.ForeignKey("Adresses", on_delete=models.DO_NOTHING, verbose_name="Adresse")
    num_telephone = models.CharField(max_length=20, verbose_name="Téléphone")
    est_admin = models.BooleanField(default=False, verbose_name="Administrateur")
    utilisateur = models.OneToOneField("auth.User", on_delete=models.CASCADE, verbose_name="Utilisateur")
    

    class Meta:
        ordering = ('utilisateur__last_name', 'utilisateur__first_name', )
        verbose_name = "Client"
        verbose_name_plural = "Clients"
    def __str__(self):
        return f"{self.utilisateur.first_name} {self.utilisateur.last_name}"

class Commandes(models.Model):
    client = models.ForeignKey("Clients", on_delete=models.SET_NULL,null=True, blank=True, verbose_name="Client")
    date_commande = models.DateTimeField(auto_now_add=True, verbose_name="Date de la commande")
    STATUT_CHOIX = [
        ('panier', 'Panier'),
        ('commande', 'Commandé'),
    ]
    statut = models.CharField(max_length=20, choices=STATUT_CHOIX, default='panier', verbose_name="Statut")

    class Meta:
        ordering = ('-date_commande', )
        verbose_name = "Commande"
        verbose_name_plural = "Commandes" 
    def __str__(self):
        return f"Commande #{self.id} - {self.client.utilisateur.username if self.client else 'Anonyme'}" 

    def get_total_amount(self):
        total = 0
        for ligne in self.lignes.all():
            total += ligne.quantite * ligne.prix_promo
        return round(total, 2)      

class CommandesProduits(models.Model):
    commande = models.ForeignKey("Commandes", on_delete=models.CASCADE, verbose_name="Commande", related_name="lignes")
    produit = models.ForeignKey("Produits", on_delete=models.CASCADE, verbose_name="Produit")
    quantite = models.IntegerField(verbose_name="Quantité")
    quantite = models.IntegerField(verbose_name="Quantité", default=1)
    prix = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Prix au moment de la commande")
    prix_promo = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Prix avec promotion appliquée", default=0.00)

    class Meta:
        verbose_name = "Produit dans la commande"
        verbose_name_plural = "Produits dans les commandes"
    def __str__(self):
        return f"{self.produit.nom_produit} x {self.quantite} dans la commande #{self.commande.id}"