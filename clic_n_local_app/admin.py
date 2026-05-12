from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.urls import reverse
from django.templatetags.static import static
from .models import Categories, Produits, Unites, Promotions, Images, PromotionsProduits


# --- INLINE IMAGES ---------------------------------------------------------
class ImagesInline(admin.TabularInline):
    model = Images
    extra = 1
    fields = ('image', 'ordre', 'principale', 'preview')
    readonly_fields = ('preview',)
    ordering = ('ordre',)

    def preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height:60px;" />', obj.image.url)
        return ""
    preview.short_description = "Aperçu"

# --- PRODUITS ADMIN ---------------------------------------------------------
@admin.register(Produits)
class ProduitsAdmin(admin.ModelAdmin):
    list_display = ('nom_produit', 'categorie', 'quantite', 'prix', 'image_principale')
    list_editable = ('quantite',)
    list_filter = ('categorie',)
    search_fields = ('nom_produit', 'description')
    ordering = ('nom_produit',)
    inlines = [ImagesInline]
    list_display_links = ('nom_produit',)

    def image_principale(self, obj):
        # Récupère la première image du produit en fonction de l'ordre
        principale = Images.objects.filter(produit_id=obj.id).order_by('ordre').first()
        if principale:
            return format_html(
                '<img src="{}" style="max-height:100px; border-radius:6px;" />',
                principale.image.url
            )
        # Image par défaut si aucune image
        return format_html(
            '<img src="{}" style="max-height:100px; opacity:0.7;" />',
            static("img/default-product-image.jpg")
        )

    image_principale.short_description = "Image principale"


# --- CATEGORIES ADMIN -------------------------------------------------------
@admin.register(Categories)
class CategoriesAdmin(admin.ModelAdmin):
    list_display = ['categorie_name_with_image', 'nb_produits']
    ordering = ['nom']
    search_fields = ['nom']
    readonly_fields = ['image_preview']

    def categorie_name_with_image(self, obj):
        image_url = obj.image.url if obj.image else static("img/default-category.png")

        return format_html(
            '<span style="display:flex; align-items:center;">'
            '<img src="{}" style="max-width:32px; margin-right:6px;" />'
            '{}'
            '</span>',
            image_url,
            obj.nom,
        )

    categorie_name_with_image.short_description = "Illustration de la catégorie"
    categorie_name_with_image.admin_order_field = 'nom'

    def nb_produits(self, obj):
        return obj.produits_set.count()   # ← adapte à ton related_name si besoin

    nb_produits.short_description = "Nombre de produits"

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-width:200px;" />', obj.image.url)
        return ""
    image_preview.short_description = "Prévisualisation de l'image"

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields
        return []



# --- UNITÉS ADMIN -----------------------------------------------------------
@admin.register(Unites)
class UnitesAdmin(admin.ModelAdmin):
    list_display = ['nom']
    ordering = ['nom']
    search_fields = ['nom']


# --- FILTRE PERSONNALISÉ POUR PROMOTIONS -----------------------------------
class PromotionActuelleFilter(admin.SimpleListFilter):
    title = "En vigueur"
    parameter_name = "en_vigueur"

    def lookups(self, request, model_admin):
        return (('oui', 'Oui'),)

    def queryset(self, request, queryset):
        if self.value() == 'oui':
            today = timezone.localdate()
            return queryset.filter(date_debut__lte=today, date_fin__gte=today)
        return queryset


# --- PROMOTIONS ADMIN -------------------------------------------------------

@admin.register(Promotions)
class PromotionsAdmin(admin.ModelAdmin):
    list_display = ['nom', 'date_debut', 'date_fin', 'description', 'view_products_link']
    ordering = ['-date_debut']
    search_fields = ['nom', 'description']
    list_filter = (PromotionActuelleFilter, 'date_debut', 'date_fin')

    def view_products_link(self, obj):
        if not obj.pk:
            return "-"
        url = reverse("admin:clic_n_local_app_promotionsproduits_changelist")
        return format_html('<a href="{}?promotion__id__exact={}">Voir les produits</a>', url, obj.id)

    view_products_link.short_description = "Produits associés"

@admin.register(PromotionsProduits)
class PromotionsProduitsAdmin(admin.ModelAdmin):
    list_display = ['produit', 'promotion', 'type', 'valeur_promo']
    ordering = ['produit', 'promotion']
    search_fields = ['produit__nom_produit', 'promotion__nom']
