from django.db.models.signals import post_delete, pre_save
from django.dispatch.dispatcher import receiver
from django.db import transaction
from .models import Categories, Images
from paypal.standard.models import ST_PP_COMPLETED
from paypal.standard.ipn.signals import valid_ipn_received
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from .models import *
import os, json

@receiver(post_delete, sender=Categories)
def categorie_post_delete(sender, instance, **kwargs):
  # Permet de supprimer l'image du produit sur le disque.
  instance.image.delete(False) # Passez False pour ne pas enregistrer le modèle.

@receiver(pre_save, sender=Categories)
def categorie_pre_save(sender, instance, **kwargs):
  if instance.pk:
    try:
      old_image = sender.objects.get(pk=instance.pk).image
      if old_image != instance.image:
        # Permet de supprimer l'ancienne image du produit sur le disque si modifiée.
        old_image.delete(False) # Passez False pour ne pas enregistrer le modèle.
    except Categories.DoesNotExist:
      pass

@receiver(pre_save, sender=Images)
def delete_old_image_on_change(sender, instance, **kwargs):
    if not instance.pk:
        return  # nouvel objet, rien à supprimer
    try:
        old_image = sender.objects.get(pk=instance.pk).image
    except sender.DoesNotExist:
        return
    new_image = instance.image
    if old_image and old_image != new_image and os.path.isfile(old_image.path):
        os.remove(old_image.path)

@receiver(post_delete, sender=Images)
def delete_image_file_on_delete(sender, instance, **kwargs):
    if instance.image and os.path.isfile(instance.image.path):
        os.remove(instance.image.path)

from django.dispatch import receiver
from paypal.standard.ipn.signals import valid_ipn_received
from paypal.standard.models import ST_PP_COMPLETED
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.db import transaction
from django.conf import settings
from decimal import Decimal


@receiver(valid_ipn_received)
def payment_notification(sender, **kwargs):
    ipn = sender

    # 1️⃣ On accepte uniquement les paiements complétés
    if ipn.payment_status != ST_PP_COMPLETED:
        return

    # 2️⃣ Récupération de la commande
    cart_id = ipn.custom
    commande = (
        Commandes.objects
        .filter(id=cart_id)
        .prefetch_related("lignes__produit")
        .select_related("client")
        .first()
    )

    if not commande:
        return

    # 3️⃣ Vérification du stock
    for ligne in commande.lignes.all():
        produit = ligne.produit
        if produit.quantite < ligne.quantite:
            print("❌ STOCK INSUFFISANT — REFUND AUTOMATIQUE")

            commande.statut = "refunded"
            commande.save(update_fields=["statut"])

            email = EmailMultiAlternatives(
                subject="Paiement remboursé – Stock indisponible",
                body=(
                    f"Bonjour {commande.client.utilisateur.first_name},\n\n"
                    f"Votre commande #{commande.id} a été remboursée automatiquement "
                    f"car un ou plusieurs articles n’étaient plus disponibles.\n\n"
                    "Nous sommes désolés pour la gêne occasionnée."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[commande.client.utilisateur.email],
            )
            email.send()
            return

    # 4️⃣ Décrément du stock + validation commande
    with transaction.atomic():
        for ligne in commande.lignes.all():
            produit = ligne.produit
            produit.quantite -= ligne.quantite
            produit.save(update_fields=["quantite"])

        commande.statut = "commande"
        commande.save(update_fields=["statut"])

    print(f"✔ Commande #{commande.id} confirmée — Stock ajusté")

    # 5️⃣ CALCUL DES MONTANTS
    for l in commande.lignes.all():
            l.rabais = l.prix - l.prix_promo
            l.prix_final = l.prix_promo
            l.sous_total = l.prix_final * l.quantite
    subtotal = commande.get_total_amount()

    # 👉 Taxes Canada (exemple QC)
    TPS_RATE = Decimal("0.05")
    TVQ_RATE = Decimal("0.09975")

    tps = subtotal * TPS_RATE
    tvq = subtotal * TVQ_RATE
    taxes = (tps + tvq).quantize(Decimal("0.01"))

    total = (subtotal + taxes).quantize(Decimal("0.01"))

    # 6️⃣ CONTEXT POUR LE TEMPLATE EMAIL
    client = commande.client
    adresse = commande.client.adresse

    context = {
        "client": client,
        "commande": commande,
        "lignes": commande.lignes.all(),
        "adresse": adresse,

        # montants
        "subtotal": subtotal.quantize(Decimal("0.01")),
        "taxes": taxes,
        "total": total,

        # paiement
        "payment_method": "PayPal",
        "payment_id": ipn.txn_id,

        # site
        "site_name": "Clic N Local",
    }

    # 7️⃣ EMAIL HTML + TEXTE
    html_content = render_to_string("emails/confirmation_achat.html", context)

    text_body = f"""
Bonjour {client.utilisateur.first_name},

Votre paiement a été confirmé avec succès.

Commande : #{commande.id}
Sous-total : {context['subtotal']} $
Taxes : {context['taxes']} $
Total payé : {context['total']} $

Adresse de livraison :
{adresse.numero} {adresse.rue}
{adresse.ville}, {adresse.province} {adresse.code_postal}

Merci pour votre confiance,
L’équipe Clic N Local
"""

    email = EmailMultiAlternatives(
        subject=f"Confirmation de votre commande #{commande.id}",
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[client.utilisateur.email],
    )
    email.attach_alternative(html_content, "text/html")
    email.send()

    print(f"📧 Email de confirmation envoyé à {client.utilisateur.email}")

