<script setup lang="ts">
import { useQuery } from '@tanstack/vue-query'
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { fetchInstallationSettings } from '../api/settings'
import { websiteHref } from '../composables/useWebsiteHref'

const { t } = useI18n()
const { data: settings, isLoading } = useQuery({
  queryKey: ['settings'],
  queryFn: fetchInstallationSettings,
})

const title = computed(() => settings.value?.title?.trim() || t('app.productName'))
const legalName = computed(() => settings.value?.legalName?.trim() || '')
const legalAddress = computed(() => settings.value?.legalAddress?.trim() || '')
const email = computed(() => settings.value?.email?.trim() || '')
const phone = computed(() => settings.value?.phone?.trim() || '')
const hasController = computed(
  () => !!(legalName.value || legalAddress.value || email.value || phone.value),
)

const hostName = computed(() => settings.value?.hostName?.trim() || '')
const hostAddress = computed(() => settings.value?.hostAddress?.trim() || '')
const hostPrivacyUrl = computed(() => websiteHref(settings.value?.hostPrivacyUrl))
const authProviderName = computed(() => settings.value?.authProviderName?.trim() || '')
const authProviderSameHost = computed(() => settings.value?.authProviderSameHost === true)
const authorityName = computed(() => settings.value?.authorityName?.trim() || '')
const authorityUrl = computed(() => websiteHref(settings.value?.authorityUrl))

const showAuthSameHostNote = computed(
  () => authProviderSameHost.value && hostName.value.length > 0 && authProviderName.value.length > 0,
)
</script>

<template>
  <div class="app-page max-w-3xl space-y-8 text-sm leading-relaxed">
    <header class="space-y-3">
      <h1 class="text-2xl font-bold">{{ t('privacy.heading') }}</h1>
      <p>
        Diese Erklärung beschreibt, welche personenbezogenen Daten bei der Nutzung von
        {{ title }} verarbeitet werden. Die Anwendung setzt keine Reichweitenmessung und keine
        Werbung ein.
      </p>
    </header>

    <section class="space-y-3">
      <h2 class="text-lg font-medium">1. Verantwortliche Stelle</h2>
      <p>
        Verantwortlich für die Datenverarbeitung in dieser Installation ist der im
        <RouterLink to="/impressum" class="link">Impressum</RouterLink>
        genannte Anbieter.
      </p>
      <p v-if="isLoading">{{ t('auth.loading') }}</p>
      <address v-else-if="hasController" class="not-italic">
        <p v-if="legalName" class="font-medium">{{ legalName }}</p>
        <p v-if="legalAddress" class="whitespace-pre-wrap">{{ legalAddress }}</p>
        <p v-if="phone">Telefon: {{ phone }}</p>
        <p v-if="email">
          E-Mail:
          <a class="link" :href="`mailto:${email}`">{{ email }}</a>
        </p>
      </address>
      <p v-else class="opacity-70">{{ t('impressum.empty') }}</p>
    </section>

    <section class="space-y-3">
      <h2 class="text-lg font-medium">2. Hosting</h2>
      <p>
        Die Anwendung wird auf einem Server des Betreibers gehostet. Dabei können technisch
        erforderliche Zugriffsdaten anfallen, insbesondere IP-Adresse, Datum und Uhrzeit des
        Abrufs, aufgerufene Adresse und Browserkennung. Sie dienen dem Betrieb, der Sicherheit
        und der Fehleranalyse.
      </p>
      <template v-if="!isLoading">
        <div v-if="hostName" class="space-y-1">
          <p>
            Auftragsverarbeiter ist {{ hostName }} (Art. 28 DSGVO). Die Daten werden nur nach
            Weisung des Betreibers verarbeitet. Dazu gehört der Versand transaktionaler E-Mails
            über den dort betriebenen SMTP-Server: Empfängeradresse, Betreff und Inhalt werden
            nur zum Zustellen verarbeitet.
          </p>
          <p v-if="hostAddress" class="whitespace-pre-wrap">{{ hostAddress }}</p>
          <p v-if="hostPrivacyUrl">
            Hinweise zum Datenschutz beim Hoster:
            <a
              :href="hostPrivacyUrl"
              class="link"
              target="_blank"
              rel="noopener noreferrer"
              >{{ settings?.hostPrivacyUrl }}</a
            >.
          </p>
        </div>
        <p v-else class="opacity-70">{{ t('privacy.hostNotConfigured') }}</p>
        <p>
          Soweit der SMTP-Server nicht beim Betreiber selbst liegt, verarbeitet auch dieser
          Dienst Empfängeradresse, Betreff und Inhalt nur zum Versand und ist
          Auftragsverarbeiter nach Art. 28 DSGVO.
        </p>
      </template>
      <p>
        Rechtsgrundlage für den Betrieb ist Art. 6 Abs. 1 lit. f DSGVO. Das berechtigte
        Interesse ist ein sicherer und funktionsfähiger Betrieb. Die Daten bleiben nur so
        lange gespeichert, wie es für diesen Zweck nötig ist.
      </p>
    </section>

    <section class="space-y-3">
      <h2 class="text-lg font-medium">3. Cookies und lokaler Speicher</h2>
      <p>
        Für die Anmeldung setzt der Server ein Sitzungs-Cookie. Skripte im Browser können es
        nicht auslesen (HttpOnly). Es wird mit SameSite Lax gesendet und endet mit dem
        Schließen des Browsers bzw. mit dem Abmelden. Darin stehen die für die Sitzung nötigen
        Anmeldedaten (Kennung, Name, E-Mail), signiert durch den Server.
      </p>
      <p>
        Im lokalen Speicher des Browsers merkt sich die Anwendung außerdem die gewählte
        Darstellung (hell oder dunkel), ob die Seitenleiste aufgeklappt ist, und das zuletzt
        gewählte Inventar. Diese Angaben verlassen das Gerät nicht und dienen nur der
        Bedienung.
      </p>
      <p>
        Beides ist erforderlich, um die Anwendung bereitzustellen (§ 25 Abs. 2 Nr. 2 TDDDG,
        Art. 6 Abs. 1 lit. b und lit. f DSGVO). Ein Einwilligungsbanner ist dafür nicht
        vorgesehen. Wer Cookies oder den lokalen Speicher im Browser sperrt, kann sich nicht
        anmelden oder verliert diese Einstellungen.
      </p>
    </section>

    <section class="space-y-3">
      <h2 class="text-lg font-medium">4. Anmeldung</h2>
      <template v-if="!isLoading">
        <p v-if="authProviderName">
          Der Zugang läuft über OpenID Connect zu {{ authProviderName }}. Beim Anmelden leitet
          die Anwendung dorthin weiter. Der Anmelde-Dienst verarbeitet die Anmeldung,
          insbesondere Nutzerkennung, Name, E-Mail-Adresse und die dabei anfallende IP-Adresse.
          <template v-if="showAuthSameHostNote">
            Dieser Dienst wird beim selben Auftragsverarbeiter wie die Anwendung betrieben.
          </template>
        </p>
        <p v-else>
          Der Zugang läuft über OpenID Connect. Beim Anmelden leitet die Anwendung zum
          konfigurierten Identitätsanbieter weiter. Dieser verarbeitet die Anmeldung in eigener
          Verantwortung.
        </p>
      </template>
      <p v-else>{{ t('auth.loading') }}</p>
      <p>
        Zurück in dieser Anwendung werden Nutzerkennung (sub), Anzeigename und E-Mail-Adresse
        gespeichert, soweit der Anmelde-Dienst sie übermittelt. Damit werden Konto,
        Berechtigungen und die Zuordnung als Verantwortliche*r eines Verleihs geführt.
      </p>
      <p>
        Rechtsgrundlage ist Art. 6 Abs. 1 lit. b DSGVO, soweit die Nutzung zur Mitgliedschaft
        oder zur beauftragten Tätigkeit gehört, sonst Art. 6 Abs. 1 lit. f DSGVO für den
        Betrieb der Inventarverwaltung. Die Daten bleiben gespeichert, solange das Konto
        besteht.
      </p>
    </section>

    <section class="space-y-3">
      <h2 class="text-lg font-medium">5. Inventar und Verleih</h2>
      <p>
        Berechtigte Personen erfassen Material, Sets, Mengen, Schäden und Verleihe. Dabei
        können personenbezogene Angaben anfallen, insbesondere Namen von Gruppen und
        Veranstaltungen, die als Verantwortliche*r eingetragene Person sowie Anschriften von
        Inventarstandorten.
      </p>
      <p>
        Die Verarbeitung ist nötig, um Ausleihe und Bestand zu führen (Art. 6 Abs. 1 lit. b
        und lit. f DSGVO). Die Angaben bleiben gespeichert, solange das Inventar sie für
        diesen Zweck braucht, und werden gelöscht, wenn der zugehörige Datensatz gelöscht
        wird.
      </p>
    </section>

    <section class="space-y-3">
      <h2 class="text-lg font-medium">6. Karte und Adresssuche</h2>
      <p>
        Standorte können auf einer Karte gesetzt werden. Die Kacheln lädt der Browser dann von
        <a
          href="https://openfreemap.org"
          class="link"
          target="_blank"
          rel="noopener noreferrer"
          >OpenFreeMap</a
        >
        (Kartendaten von OpenStreetMap). Dabei werden die IP-Adresse und technische
        Verbindungsdaten an den Kachelserver übermittelt. Die Karte erscheint nur in
        Formularen für Standorte, nicht auf jeder Seite.
      </p>
      <p>
        Die Suche nach einer Adresse läuft über den eigenen Server. Der Server fragt
        <a
          href="https://nominatim.openstreetmap.org"
          class="link"
          target="_blank"
          rel="noopener noreferrer"
          >Nominatim</a
        >
        (OpenStreetMap) mit dem eingegebenen Suchtext an. An Nominatim geht dabei die
        Adressanfrage und die IP-Adresse des Servers, nicht die des Browsers.
      </p>
      <p>
        Rechtsgrundlage ist Art. 6 Abs. 1 lit. f DSGVO: Standorte sollen auffindbar sein.
        Hinweise zum Datenschutz bei OpenStreetMap:
        <a
          href="https://wiki.osmfoundation.org/wiki/Privacy_Policy"
          class="link"
          target="_blank"
          rel="noopener noreferrer"
          >Privacy Policy der OpenStreetMap Foundation</a
        >.
      </p>
    </section>

    <section class="space-y-3">
      <h2 class="text-lg font-medium">7. E-Mail</h2>
      <p>
        Die Anwendung versendet nur Nachrichten, die eine Nutzung auslöst, etwa zum Konto, zu
        einem Verleih oder einer Reservierung, oder eine Testmail aus der Diagnose. Es gibt
        keine Werbung und keinen Newsletter.
      </p>
      <p>
        Verarbeitet werden die E-Mail-Adresse, der Name soweit vorhanden, und der Inhalt der
        Nachricht. Rechtsgrundlage ist Art. 6 Abs. 1 lit. b DSGVO, soweit die Nachricht zur
        Nutzung gehört, sonst Art. 6 Abs. 1 lit. f DSGVO für den Betrieb der Anwendung.
      </p>
      <p>
        Die Anwendung speichert die Nachricht nicht. Der Versanddienst kann technische
        Protokolle führen, solange das für Betrieb und Zustellung nötig ist. Ihre Rechte dazu
        stehen im folgenden Abschnitt.
      </p>
    </section>

    <section class="space-y-3">
      <h2 class="text-lg font-medium">8. Ihre Rechte</h2>
      <p>
        Sie können Auskunft über die zu Ihrer Person gespeicherten Daten verlangen, außerdem
        Berichtigung, Löschung und Einschränkung der Verarbeitung sowie, soweit die
        Voraussetzungen vorliegen, Datenübertragbarkeit. Eine Einwilligung können Sie für die
        Zukunft widerrufen.
      </p>
      <p>
        Beruht eine Verarbeitung auf Art. 6 Abs. 1 lit. e oder lit. f DSGVO, können Sie aus
        Gründen, die sich aus Ihrer besonderen Situation ergeben, widersprechen. Wir
        verarbeiten die Daten dann nicht weiter, es sei denn, es liegen zwingende schutzwürdige
        Gründe vor oder die Verarbeitung dient der Geltendmachung von Rechtsansprüchen.
      </p>
      <p>
        Außerdem haben Sie das Recht, sich bei einer Datenschutz-Aufsichtsbehörde zu
        beschweren, insbesondere in dem Mitgliedstaat Ihres Aufenthaltsorts, Ihres
        Arbeitsplatzes oder des Orts des mutmaßlichen Verstoßes.
        <template v-if="authorityName">
          Zuständig kann insbesondere
          <a
            v-if="authorityUrl"
            :href="authorityUrl"
            class="link"
            target="_blank"
            rel="noopener noreferrer"
            >{{ authorityName }}</a
          >
          <template v-else>{{ authorityName }}</template>
          sein.
        </template>
      </p>
      <p>Für diese Rechte und weitere Fragen erreichen Sie die verantwortliche Stelle über die oben genannten Kontaktdaten.</p>
    </section>
  </div>
</template>
