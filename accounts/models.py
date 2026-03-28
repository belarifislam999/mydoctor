from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator

# ── 69 Wilayas d'Algérie ─────────────────────────────────────
WILAYAS = [
    ('01','01 - Adrar'), ('02','02 - Chlef'), ('03','03 - Laghouat'),
    ('04','04 - Oum El Bouaghi'), ('05','05 - Batna'), ('06','06 - Béjaïa'),
    ('07','07 - Biskra'), ('08','08 - Béchar'), ('09','09 - Blida'),
    ('10','10 - Bouira'), ('11','11 - Tamanrasset'), ('12','12 - Tébessa'),
    ('13','13 - Tlemcen'), ('14','14 - Tiaret'), ('15','15 - Tizi Ouzou'),
    ('16','16 - Alger'), ('17','17 - Djelfa'), ('18','18 - Jijel'),
    ('19','19 - Sétif'), ('20','20 - Saïda'), ('21','21 - Skikda'),
    ('22','22 - Sidi Bel Abbès'), ('23','23 - Annaba'), ('24','24 - Guelma'),
    ('25','25 - Constantine'), ('26','26 - Médéa'), ('27','27 - Mostaganem'),
    ('28',"28 - M'Sila"), ('29','29 - Mascara'), ('30','30 - Ouargla'),
    ('31','31 - Oran'), ('32','32 - El Bayadh'), ('33','33 - Illizi'),
    ('34','34 - Bordj Bou Arréridj'), ('35','35 - Boumerdès'), ('36','36 - El Tarf'),
    ('37','37 - Tindouf'), ('38','38 - Tissemsilt'), ('39','39 - El Oued'),
    ('40','40 - Khenchela'), ('41','41 - Souk Ahras'), ('42','42 - Tipaza'),
    ('43','43 - Mila'), ('44','44 - Aïn Defla'), ('45','45 - Naâma'),
    ('46','46 - Aïn Témouchent'), ('47','47 - Ghardaïa'), ('48','48 - Relizane'),
    ('49','49 - Timimoun'), ('50','50 - Bordj Badji Mokhtar'),
    ('51','51 - Ouled Djellal'), ('52','52 - Béni Abbès'),
    ('53','53 - In Salah'), ('54','54 - In Guezzam'),
    ('55','55 - Touggourt'), ('56','56 - Djanet'),
    ('57',"57 - El M'Ghair"), ('58','58 - El Meniaa'),
    ('59','59 - El Bayadh Nord'), ('60','60 - Ain Témouchent Sud'),
    ('61','61 - Relizane Nord'), ('62','62 - Sig'),
    ('63','63 - Mostaganem Est'), ('64','64 - Oran Est'),
    ('65','65 - Alger Ouest'), ('66','66 - Alger Est'),
    ('67','67 - Blida Nord'), ('68','68 - Médéa Nord'),
    ('69','69 - Boumerdès Nord'),
]

phone_validator = RegexValidator(
    regex=r'^\+?[0-9]{9,15}$',
    message="Numéro de téléphone invalide."
)


class User(AbstractUser):
    ROLE_DOCTOR  = 'doctor'
    ROLE_PATIENT = 'patient'
    ROLE_CHOICES = [
        (ROLE_DOCTOR,  'Médecin'),
        (ROLE_PATIENT, 'Patient'),
    ]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=ROLE_PATIENT)

    # Email unique obligatoire
    email = models.EmailField(unique=True, blank=False)

    # Téléphone unique
    phone_number = models.CharField(
        max_length=20, blank=True, null=True,
        unique=True,
        validators=[phone_validator],
        verbose_name="Téléphone"
    )
    profile_picture = models.ImageField(
        upload_to='profile_pics/', blank=True, null=True,
        verbose_name="Photo de profil"
    )

    def is_doctor(self):
        return self.role == self.ROLE_DOCTOR

    def is_patient(self):
        return self.role == self.ROLE_PATIENT

    def __str__(self):
        if self.is_doctor():
            return f"Dr. {self.get_full_name() or self.username}"
        return self.get_full_name() or self.username

    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"


class DoctorProfile(models.Model):
    SPECIALIZATIONS = [
        ('generaliste',   'Médecin Généraliste'),
        ('cardiologie',   'Cardiologie'),
        ('dermatologie',  'Dermatologie'),
        ('neurologie',    'Neurologie'),
        ('orthopedie',    'Orthopédie'),
        ('pediatrie',     'Pédiatrie'),
        ('psychiatrie',   'Psychiatrie'),
        ('gynecologie',   'Gynécologie'),
        ('ophtalmologie', 'Ophtalmologie'),
        ('orl',           'ORL'),
        ('radiologie',    'Radiologie'),
        ('oncologie',     'Oncologie'),
        ('urologie',      'Urologie'),
        ('dentiste',      'Dentiste'),
        ('autre',         'Autre'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='doctor_profile')
    specialization = models.CharField(max_length=50, choices=SPECIALIZATIONS, default='generaliste', verbose_name="Spécialisation")
    wilaya    = models.CharField(max_length=3, choices=WILAYAS, default='16', verbose_name="Wilaya")
    commune   = models.CharField(max_length=100, blank=True, verbose_name="Commune")
    bio       = models.TextField(blank=True, verbose_name="Biographie")
    years_of_experience = models.PositiveIntegerField(default=0, verbose_name="Années d'expérience")
    consultation_fee    = models.DecimalField(max_digits=8, decimal_places=2, default=0.00, verbose_name="Tarif (DA)")
    clinic_address = models.TextField(blank=True, verbose_name="Adresse du cabinet")
    is_available   = models.BooleanField(default=True, verbose_name="Disponible")

    def __str__(self):
        return f"Dr. {self.user.get_full_name()} — {self.get_specialization_display()}"

    def get_wilaya_name(self):
        return dict(WILAYAS).get(self.wilaya, '')

    class Meta:
        verbose_name = "Profil Médecin"
        verbose_name_plural = "Profils Médecins"


class PatientProfile(models.Model):
    BLOOD_GROUPS = [
        ('A+','A+'),('A-','A-'),('B+','B+'),('B-','B-'),
        ('AB+','AB+'),('AB-','AB-'),('O+','O+'),('O-','O-'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='patient_profile')
    date_of_birth  = models.DateField(blank=True, null=True, verbose_name="Date de naissance")
    blood_group    = models.CharField(max_length=5, choices=BLOOD_GROUPS, blank=True, verbose_name="Groupe sanguin")
    allergies      = models.TextField(blank=True, verbose_name="Allergies")
    medical_history = models.TextField(blank=True, verbose_name="Antécédents médicaux")
    emergency_contact_name  = models.CharField(max_length=100, blank=True, verbose_name="Contact d'urgence")
    emergency_contact_phone = models.CharField(max_length=20,  blank=True, verbose_name="Téléphone d'urgence")
    wilaya = models.CharField(max_length=3, choices=WILAYAS, blank=True, verbose_name="Wilaya")

    def __str__(self):
        return f"Patient: {self.user.get_full_name() or self.user.username}"

    class Meta:
        verbose_name = "Profil Patient"
        verbose_name_plural = "Profils Patients"


class Advertisement(models.Model):
    POSITION_CHOICES = [
        ('hero',    'Bannière principale (Hero)'),
        ('top',     'En haut de page'),
        ('sidebar', 'Barre latérale'),
        ('bottom',  'Bas de page'),
    ]
    title       = models.CharField(max_length=200, verbose_name="Titre")
    description = models.TextField(blank=True, verbose_name="Description")
    image       = models.ImageField(upload_to='ads/', blank=True, null=True, verbose_name="Image")
    link_url    = models.URLField(blank=True, verbose_name="Lien URL")
    link_text   = models.CharField(max_length=100, blank=True, default="En savoir plus", verbose_name="Texte du bouton")
    position    = models.CharField(max_length=20, choices=POSITION_CHOICES, default='top', verbose_name="Position")
    is_active   = models.BooleanField(default=True, verbose_name="Actif")
    background_color = models.CharField(max_length=20, default='#f0f7ff', verbose_name="Couleur de fond")
    text_color       = models.CharField(max_length=20, default='#1e3a5f', verbose_name="Couleur du texte")
    created_at  = models.DateTimeField(auto_now_add=True)
    order       = models.PositiveIntegerField(default=0, verbose_name="Ordre")

    class Meta:
        ordering = ['order', '-created_at']
        verbose_name = "Publicité"
        verbose_name_plural = "Publicités"

    def __str__(self):
        return f"{self.title} [{self.get_position_display()}]"
