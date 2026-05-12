from pyexpat.errors import messages
from django.shortcuts import render, get_object_or_404
from django.views import View
from django.http import Http404
from django.shortcuts import render, get_object_or_404, redirect
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from paypal.standard.forms import PayPalPaymentsForm
import uuid, json
from django.urls import reverse, reverse_lazy
from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from .forms import ContactForm, UserRegistrationForm, ProfileUpdateForm, MyPasswordChangeForm
from django.core.paginator import Paginator
from .models import *
from django.db import transaction
from django.contrib.auth.views import LoginView
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.contrib.auth.views import PasswordChangeView
from django.contrib.auth.mixins import LoginRequiredMixin
from decimal import Decimal, ROUND_HALF_UP

def about(request):
    return render(request, 'about.html')

def produit_detail(request, produit_id):
    produit = get_object_or_404(Produits, id=produit_id)

    # Récupération des images
    images = produit.images.all()
    image_principale = images.order_by('ordre').first()

    if not image_principale:
        # Objet fictif si pas d'image
        class DummyImage:
            image = type('obj', (object,), {'url': '/static/img/default-product-image.jpg'})()
        image_principale = DummyImage()

    # Gestion de la promotion et prix final
    promotion_active = produit.get_active_promotion() if hasattr(produit, 'get_active_promotion') else None
    prix_final = produit.get_discounted_price() if hasattr(produit, 'get_discounted_price') else produit.prix

    promotion_info = None
    if promotion_active:
        promotion_info = {
            "nom": promotion_active.promotion.nom,
            "description": promotion_active.promotion.description,
            "date_debut": promotion_active.promotion.date_debut,
            "date_fin": promotion_active.promotion.date_fin,
            "type": promotion_active.type,
            "valeur_promo": promotion_active.valeur_promo,
        }

    return render(request, "produit-detail.html", {
        "produit": produit,
        "images": images,
        "image_principale": image_principale,
        "promotion": promotion_active,
        "prix_final": prix_final,
        "promotion_info": promotion_info,
    })

def cart_detail(request):
    if request.user.is_authenticated:
        items = CommandesProduits.objects.filter(
            commande__client__utilisateur=request.user,
            commande__statut='panier'
        )

        # enrichir chaque item avec un champ calculé
        for item in items:
            if item.prix_promo and item.prix_promo > 0:
                item.rabais = float(item.prix) - float(item.prix_promo)
            else:
                item.rabais = 0

        # calcul du total avec prix promo si dispo
        total = 0
        for item in items:
            if item.prix_promo and item.prix_promo > 0:
                total += float(item.prix_promo) * item.quantite
            else:
                total += float(item.prix) * item.quantite
    else:
        items = []
        total = 0

    return render(request, 'cart_detail.html', {
        'items': items,
        'total': total
    })

def update_cart_item(request, item_id):
    if request.method == "POST" and request.user.is_authenticated:
        item = get_object_or_404(
            CommandesProduits,
            id=item_id,
            commande__client__utilisateur=request.user,
            commande__statut='panier'
        )
        produit = item.produit

        try:
            new_quantity = int(request.POST.get("quantity", item.quantite))

            if new_quantity > 0:
                # On remet l'ancienne quantité en stock avant de recalculer
                produit.quantite += item.quantite

                # Vérification : ne pas dépasser le stock disponible
                if new_quantity > produit.quantite:
                    # si demande trop grande, on limite au stock dispo
                    new_quantity = produit.quantite

                # Mise à jour du stock
                produit.quantite -= new_quantity
                produit.save()

                # Mise à jour de la ligne
                item.quantite = new_quantity
                item.save()

            else:
                # Si quantité <= 0 → suppression de la ligne et restitution du stock
                produit.quantite += item.quantite
                produit.save()
                item.delete()

        except ValueError:
            pass  # ignore si la valeur n'est pas un entier

    return redirect("cart_detail")

@transaction.atomic
def add_to_cart(request, produit_id):
    produit = get_object_or_404(Produits, id=produit_id)

    if request.method != "POST":
        return redirect("produits_list", produit_id=produit_id)

    # Quantité envoyée depuis le formulaire
    try:
        quantite = int(request.POST.get("quantity", 1))
    except ValueError:
        quantite = 1

    if quantite < 1:
        quantite = 1

    # Vérifier stock
    if produit.quantite < quantite:
        return redirect("produit-detail", produit_id=produit_id)

    # Ouvrir la transaction
    with transaction.atomic():

        # Récupérer ou créer le panier du client
        commande, created = Commandes.objects.get_or_create(
            client=request.user.clients,
            statut="panier"
        )

        promo = produit.get_active_promotion()
        if promo:
            prix_promo = promo.get_discounted_price(produit.prix)
        else:
            prix_promo = produit.prix

        # Vérifier si le produit est déjà dans le panier
        ligne, ligne_created = CommandesProduits.objects.get_or_create(
            commande=commande,
            produit=produit,
            defaults={
                "quantite": quantite,
                "prix": produit.prix,   # prix au moment de la commande
                "prix_promo": prix_promo
            }
        )

        if not ligne_created:
            # Mise à jour de la quantité
            nouvelle_quantite = ligne.quantite + quantite

            # Double vérification stock en transaction
            if nouvelle_quantite > produit.quantite:
                return redirect("produit-detail", produit_id=produit_id)

            ligne.quantite = nouvelle_quantite
            ligne.save()

        # Mise à jour du stock produit
        produit.quantite -= quantite
        produit.save()

    return redirect("produits_list")

class ContactView(View):
    def get(self, request):
        if request.user.is_authenticated:
            initial_data = {
                "name": request.user.get_full_name() or request.user.username,
                "email": request.user.email,
            }
            form = ContactForm(initial=initial_data)
        else:
            form = ContactForm()

        success = request.GET.get("success") == "1"

        return render(request, "contact.html", {
            "form": form,
            "success": success
        })

    def post(self, request):
        form = ContactForm(request.POST)

        if form.is_valid():
            name = form.cleaned_data["name"]
            email = form.cleaned_data["email"]
            subject = form.cleaned_data["subject"]
            message = form.cleaned_data["message"]

            # Contenu
            text_content = f"Message de {name} ({email})\n\n{message}"
            html_content = f"""
                <h2>Nouveau message de contact</h2>
                <p><strong>Nom:</strong> {name}</p>
                <p><strong>Email:</strong> {email}</p>
                <p><strong>Sujet:</strong> {subject}</p>
                <p><strong>Message:</strong><br>{message}</p>
            """

            try:
                # Email vers toi
                msg = EmailMultiAlternatives(
                    subject=f"[Contact] {subject}",
                    body=text_content,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[settings.DEFAULT_FROM_EMAIL],
                    reply_to=[email]
                )
                msg.attach_alternative(html_content, "text/html")
                msg.send()

                # Copie à l'utilisateur
                html_content = render_to_string(
                    "emails/ContactMail.html",
                    {
                        "name": name,
                        "email": email,
                        "subject": subject,
                        "message": message,
                        "site_url": request.build_absolute_uri('/'),
                    }
                )

                copy = EmailMultiAlternatives(
                    subject=f"Copie de votre message – {subject}",
                    body="Votre client email ne supporte pas le HTML.",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[email],
                )

                copy.attach_alternative(html_content, "text/html")
                copy.send()

            except Exception as e:
                messages.error(request, "❌ Une erreur est survenue lors de l’envoi du message. Veuillez réessayer.")
                return render(request, "contact.html", {"form": form})

            return redirect("/contact/success/")

        return render(request, "contact.html", {"form": form})


def contact_success_view(request):
    return render(request, "contact_success.html")

def inscription_succes_view(request):
    return render(request, "inscription_succes.html")

class ProduitsListView(View):
    def get(self, request):
        category_id = request.GET.get('category')
        price_min = request.GET.get('price_min')
        price_max = request.GET.get('price_max')
        search = request.GET.get('search')
        promo_ids = self.request.GET.getlist("promo")
        sort = request.GET.get('sort') or "nom_produit"

        today = timezone.now().date()
        promotions = Promotions.objects.filter(Q(date_fin__gte=today) | Q(date_fin__isnull=True) , Q(date_debut__lte=today)).distinct()
        listProduits = Produits.objects.all().select_related("categorie").prefetch_related("images")
        listCategories = Categories.objects.all()

        if category_id :
            listProduits = listProduits.filter(categorie_id=category_id)
        if price_max:
            try:
                listProduits = listProduits.filter(prix__lte=float(price_max))
            except ValueError:
                pass
        if price_min:
            try:
                listProduits = listProduits.filter(prix__gte=float(price_min))
            except ValueError:
                pass
        if search:
            keywords = search.split()
            for word in keywords:
                listProduits = listProduits.filter(
                    Q(nom_produit__icontains=word) |
                    Q(description__icontains=word)
                )
        # if promo_active:
        #     listProduits = listProduits.filter(
        #         Q(promotionsproduits__promotion__date_fin__gte=today) |
        #         Q(promotionsproduits__promotion__date_fin__isnull=True),
        #         promotionsproduits__promotion__date_debut__lte=today
        #     ).distinct()
        selected_promos = request.GET.getlist("promo")
        # Si promo=all → sélectionner toutes les promotions actives
        if "all" in selected_promos:
            selected_promos = [str(p.id) for p in promotions]  # liste de tous les IDs actifs

        if selected_promos:
            listProduits = listProduits.filter(
                promotionsproduits__promotion__id__in=selected_promos
            ).distinct()



        listProduits = listProduits.order_by(sort)
        paginator = Paginator(listProduits, 15)  # 15 produits par page
        page_number = request.GET.get('page')      # récupère ?page=1, ?page=2...
        page_obj = paginator.get_page(page_number) # page courante
        for p in page_obj:
            p.active_promo = p.get_active_promotion

        return render(request, 'Liste_produits.html', {
            'produits': listProduits,
            "page_obj": page_obj,
            'categories': listCategories,
            'promotions': promotions,
            'selected_promos': [int(p) for p in selected_promos]
        })

class IndexView(View):
    def get(self, request):
        categories = list(Categories.objects.all())

        # Grouper les catégories par 3 pour le slider
        categories_grouped = [categories[i:i + 3] for i in range(0, len(categories), 3)]

        # Récupérer les 4 produits les plus récents avec informations de promotion
        produits_recents = Produits.objects.select_related('categorie', 'unite_de_vente').prefetch_related(
            'images', 'promotionsproduits_set__promotion').order_by('-id')[:4]
        
        # Ajouter les informations de promotion aux produits récents
        for produit in produits_recents:
            active_promo = produit.get_active_promotion()
            if active_promo:
                produit.prix_reduit = produit.get_discounted_price()
                produit.promotions_actives = [active_promo]
                produit.a_promotion = True
            else:
                produit.a_promotion = False

        produit_promo = []
        for produit in Produits.objects.select_related('categorie', 'unite_de_vente').prefetch_related('images',
                                                                                                       'promotionsproduits_set__promotion').all():
            active_promo = produit.get_active_promotion()
            if active_promo:
                # Ajouter les informations de promotion au produit
                produit.prix_reduit = produit.get_discounted_price()
                produit.promotions_actives = [active_promo]  # Mettre dans une liste pour la template
                produit_promo.append(produit)

        promotion_grouped = [produit_promo[i:i + 3] for i in range(0, len(produit_promo), 3)]

        context = {
            'categories': categories,
            'categories_grouped': categories_grouped,
            'produits_recents': produits_recents,
            'produit_en_promotion': produit_promo,
            'promotion_grouped': promotion_grouped,
        }

        return render(request, 'index.html', context)


# PayPal Views pour tester PayPalPaymentsForm

def view_paypal_success(request):

    payer_id = request.GET.get("PayerID")
    if not payer_id:
        return redirect("index")

    client = request.user.clients
    commande = Commandes.objects.filter(client=client, statut="panier").order_by("-date_commande").first()

    if not commande:
        commande = Commandes.objects.filter(client=client, statut="commande").order_by("-date_commande").first()

    if not commande:
        return render(request, "payement_success.html", {"en_attente": True})
    
    lignes = commande.lignes.all()
    total = commande.get_total_amount()
    TPS_TAUX = Decimal("0.05")
    TVQ_TAUX = Decimal("0.09975")

    tps = (total * TPS_TAUX).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    tvq = (total * TVQ_TAUX).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    total_taxes = (tps + tvq).quantize(Decimal("0.01"))
    total_avec_taxes = (total + total_taxes).quantize(Decimal("0.01"))

    return render(request, "payement_success.html", {
        "commande": commande,
        "lignes": lignes,
        "total": total_avec_taxes
    })

def view_paypal_cancel(request):
    return render(request, "payement_cancel.html")

class RecapCommandeView(View):

    def get(self, request):
        if not request.user.is_authenticated:
            return redirect("login")

        try:
            client = request.user.clients
        except Clients.DoesNotExist:
            return redirect("index")
        
        try:
            commande = Commandes.objects.get(client=client, statut="panier")
        except Commandes.DoesNotExist:
            return redirect("index")

        lignes = CommandesProduits.objects.filter(commande=commande)

        stock_insuffisant = []

        for ligne in lignes:
            produit = ligne.produit
            if ligne.quantite > produit.quantite:
                manque = ligne.quantite - produit.quantite
                stock_insuffisant.append({
                    "produit": produit,
                    "demande": ligne.quantite,
                    "disponible": produit.quantite,
                    "manque": manque,
                })

        if stock_insuffisant:
            context = {
                "stock_insuffisant": stock_insuffisant,
                "commande": commande,
                "lignes": lignes,
                "client": client,
            }
            return render(request, "Panier.html", context)

        for l in lignes:
            l.rabais = l.prix - l.prix_promo
            l.prix_final = l.prix_promo
            l.sous_total = l.prix_final * l.quantite

        adresse = client.adresse
        total = commande.get_total_amount()
        # Calcul des taxes
        TPS_TAUX = Decimal("0.05")
        TVQ_TAUX = Decimal("0.09975")

        tps = (total * TPS_TAUX).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        tvq = (total * TVQ_TAUX).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        total_taxes = (tps + tvq).quantize(Decimal("0.01"))
        total_avec_taxes = (total + total_taxes).quantize(Decimal("0.01"))

        invoice_id = str(uuid.uuid4())

        paypal_dict = {
            "business": "clic_n_local@paypal.com",
            "amount": str(total_avec_taxes),
            "currency_code": "CAD",
            "item_name": "Panier Clic N Local",
            "invoice": invoice_id,
            "notify_url": request.build_absolute_uri(reverse('paypal-ipn')),
            "return": request.build_absolute_uri(reverse('payment_success')),
            "cancel_return": request.build_absolute_uri(reverse('payment_cancel')),
            "custom": str(commande.id),
        }

        form = PayPalPaymentsForm(initial=paypal_dict)

        context = {
            "commande": commande,
            "lignes": lignes,
            "client": client,
            "adresse": adresse,
            "total": total,
            "tps": tps,
            "tvq": tvq,
            "total_taxes": total_taxes,
            "total_avec_taxes": total_avec_taxes,
            "paypal_form": form,
        }

        return render(request, "CommandeRecap.html", context)


class RegisterView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('index') 
        form = UserRegistrationForm()
        return render(request, 'register_page.html', {'form': form})

    def post(self, request):
        if request.user.is_authenticated:
            return redirect('index')
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Récupération du client créé automatiquement par le signal
            try:
                client = user.clients
                adresse = client.adresse
                
                # Préparation du contexte pour l'email
                context = {
                    'client': client,
                    'adresse': adresse,
                    'site_name': 'Clic N Local',
                    'site_url': request.build_absolute_uri('/'),
                }
                
                # Génération du contenu HTML de l'email
                html_content = render_to_string('emails/confirmation_inscription.html', context)
                
                # Contenu texte simple (fallback)
                text_content = f"""
                Bonjour {user.first_name} {user.last_name},
                
                Merci de vous être inscrit sur Clic N Local !
                
                Votre compte a été créé avec succès.
                Nom d'utilisateur : {user.username}
                Email : {user.email}
                
                Vous pouvez maintenant profiter de nos produits locaux et artisanaux.
                
                Cordialement,
                L'équipe Clic N Local
                """
                
                # Envoi de l'email
                msg = EmailMultiAlternatives(
                    subject='Bienvenue chez Clic N Local ! 🎉',
                    body=text_content,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[user.email]
                )
                msg.attach_alternative(html_content, "text/html")
                msg.send()
            except Exception as e:
                # Si l'envoi échoue, on log l'erreur mais on continue
                print(f"Erreur lors de l'envoi de l'email de confirmation : {e}")
           
            # login(request, user)
            return redirect('inscription_succes')
        return render(request, 'register_page.html', {'form': form})
    
class ClientLoginView(LoginView):
    template_name = "login.html"
    authentication_form = AuthenticationForm
    redirect_authenticated_user = True
    success_url = reverse_lazy("index")

    def get_success_url(self):
        return self.success_url

class ProfileView(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('login')
        
        form = ProfileUpdateForm(instance=request.user)
        
        context = {
            'form': form,
            'user': request.user,
        }
        
        return render(request, 'profile.html', context)
    
    def post(self, request):
        if not request.user.is_authenticated:
            return redirect('login')
        form = ProfileUpdateForm(request.POST, instance=request.user)
        
        if form.is_valid():
            form.save()
            # Message de succès (optionnel, nécessite django.contrib.messages)
            messages.success(request, 'Votre profil a été mis à jour avec succès.')
            return redirect('profile')
        
        context = {
            'form': form,
            'user': request.user,
        }
        
        return render(request, 'profile.html', context)
    
class MyPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    template_name = "password_change.html"
    success_url = reverse_lazy("password_change_done")
    login_url = "login" 
    form_class = MyPasswordChangeForm