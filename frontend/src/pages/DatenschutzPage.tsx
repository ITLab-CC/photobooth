import { Box, Typography } from "@mui/material";
import { keyframes } from "@mui/system";

const backgroundAnimation = keyframes`
  0% { background: linear-gradient(45deg, #ff9a9e, #fad0c4); }
  33% { background: linear-gradient(45deg, #fad0c4, #a18cd1); }
  66% { background: linear-gradient(45deg, #a18cd1, #fbc2eb); }
  100% { background: linear-gradient(45deg, #fbc2eb, #ff9a9e); }
`;

export default function DatenschutzPage() {
  return (
    <Box
      sx={{
        animation: `${backgroundAnimation} 15s ease infinite`,
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        p: 2,
        position: "relative",
      }}
    >
      <Box
        sx={{
          width: "80%",
          maxWidth: "800px",
          margin: "40px auto",
          padding: "20px",
          backgroundColor: "#fff",
          borderRadius: "8px",
          boxShadow: "0px 2px 8px rgba(0,0,0,0.1)",
        }}
      >
        {/* Einwilligungserklärung */}
        <Typography variant="h4" gutterBottom align="center">
          Einwilligungserklärung Datenschutz
        </Typography>
        <Typography variant="body1" paragraph>
          Für die Verarbeitung personenbezogener Daten ist eine Einwilligung der Betroffenen, bei Kindern und Jugendlichen unter 16 Jahren die der Erziehungsberechtigten erforderlich.
        </Typography>
        <Typography variant="body1" paragraph>
          <b>
            Ich bzw. mein Kind möchte an der Fotobox-Aktion teilnehmen und willige ein, dass die von mir bzw. meinem Kind angefertigten Fotoaufnahmen von der COUNT+CARE GmbH &amp; Co. KG (Verantwortlicher) verarbeitet werden dürfen zur Anfertigung von Abzügen, die mir unmittelbar vor Ort ausgehändigt werden und zur Bereitstellung dieser Fotoaufnahmen zum Download auf einem Server des Verantwortlichen.
          </b>
        </Typography>
        <Typography variant="body1" paragraph>
          Der Download erfolgt mithilfe eines QR-Codes (Internet-Link), den ich vor Ort erhalte, und einer von mir selbst individuell zu vergebenden 4-stelligen PIN-Nr. Im Downloadbereich kann ich die endgültige Löschung der Fotoaufnahmen selbst veranlassen. Sämtliche Fotoaufnahmen werden, wenn ich Löschung nicht vorher veranlasst habe, nach Ablauf von 7 Kalendertagen automatisch gelöscht.
        </Typography>
        <Typography variant="body1" paragraph>
          Soweit sich aus Fotoaufnahmen Hinweise auf meine ethnische Herkunft, Religion oder Gesundheit ergeben (z. B. Hautfarbe, Kopfbedeckung, Brille), bezieht sich meine Einwilligung auch darauf. Die Erhebung, Verarbeitung und Nutzung meiner Daten erfolgt auf freiwilliger Basis. Meine Einwilligung kann ich daher jederzeit mit Wirkung für die Zukunft widerrufen. Wenn ich widerrufe, werden meine personenbezogenen Daten unverzüglich nach Zugang der Widerrufserklärung gelöscht. Durch den Widerruf der Einwilligung wird die Rechtmäßigkeit der bis zum Widerruf erfolgten Verarbeitung nicht berührt.
        </Typography>
        <Typography variant="body1" paragraph>
          Meine Widerrufserklärung werde ich unter Beifügung des QR-Codes (zur Zuordnung) richten an:
          <br />
          COUNT+CARE GmbH &amp; Co. KG
          <br />
          C06 Neue Lösungen - Ausbildung
          <br />
          Frankfurter Straße 100
          <br />
          64293 Darmstadt
          <br />
          IT-Ausbildung@countandcare.de
        </Typography>

        {/* Datenschutzhinweise */}
        <Typography variant="h4" gutterBottom align="center" sx={{ marginTop: "40px" }}>
          Datenschutzhinweise der COUNT+CARE GMBH &amp; CO. KG
        </Typography>
        <Typography variant="body1" paragraph>
          Die nachfolgenden Datenschutzhinweise geben einen Überblick über die Erhebung und Verarbeitung Ihrer Daten.
        </Typography>
        <Typography variant="body1" paragraph>
          COUNT+CARE GMBH &amp; CO. KG nimmt Ihre Privatsphäre sehr ernst und verarbeitet Ihre personenbezogenen Daten im Einklang mit den jeweils anwendbaren gesetzlichen Datenschutzanforderungen. Personenbezogene Daten im Sinne dieser Information sind sämtliche Informationen, die einen Bezug zu Ihrer Person aufweisen können, also z. B. Name, Anschrift, E-Mail- und IP-Adresse, Nutzerverhalten.
        </Typography>
        <Typography variant="body1" paragraph>
          Mit den nachfolgenden Datenschutzhinweisen informieren wir Sie über die Verarbeitung Ihrer personenbezogenen Daten bei uns. Außerdem geben wir Ihnen einen Überblick über Ihre Datenschutzrechte. Welche Daten im Einzelnen verarbeitet und in welcher Weise genutzt werden, richtet sich maßgeblich nach der Art der geschäftlichen Beziehung, die wir mit Ihnen eingegangen sind.
        </Typography>
        <Typography variant="body1" paragraph>
          <b>Verantwortliche Stelle und Datenschutzbeauftragter</b>
          <br />
          Verantwortliche Stelle ist:
          <br />
          COUNT+CARE GMBH &amp; CO. KG
          <br />
          Frankfurter Straße 110
          <br />
          64293 Darmstadt
          <br />
          <br />
          Sie erreichen unseren Datenschutzbeauftragten unter:
          <br />
          COUNT+CARE GMBH &amp; CO. KG
          <br />
          Datenschutzbeauftragter
          <br />
          Frankfurter Straße 110
          <br />
          64293 Darmstadt
          <br />
          datenschutz@countandcare.de
        </Typography>
        <Typography variant="body1" paragraph>
          <b>Quelle der personenbezogenen Daten</b>
          <br />
          Wir verarbeiten personenbezogene Daten, die bei Fotoshootings im Rahmen der Aktion „Fotobox“ bei der „Nacht der Ausbildung“ anfallen sowie beim Abruf von Fotoaufnahmen von unserem Server / unserer Homepage.
        </Typography>
        <Typography variant="body1" paragraph>
          <b>Kategorien personenbezogener Daten, die verarbeitet werden</b>
          <br />
          Wir verarbeiten folgende Kategorien von personenbezogenen Daten: Fotoaufnahmen (sowie ggf. besondere Datentypen nach Art. 9 DSGVO wie Hautfarbe, Brille oder Kopfbedeckung), Zugangsdaten (QR-Code und PIN), IP-Adresse sowie andere mit den genannten Kategorien vergleichbare Daten.
        </Typography>
        <Typography variant="body1" paragraph>
          <b>Zwecke, für die die personenbezogenen Daten verarbeitet werden sollen und Rechtsgrundlagen der Verarbeitung</b>
          <br />
          Wir verarbeiten Ihre personenbezogenen Daten unter Einhaltung der jeweils anwendbaren gesetzlichen Datenschutzanforderungen. Dabei ist die Verarbeitung rechtmäßig, wenn nachstehende Bedingung erfüllt ist:
          <br />
          Einwilligung (Artt. 6 Abs. 1 a, 9 DSGVO)
          <br />
          Die Rechtmäßigkeit für die Verarbeitung personenbezogener Daten ist bei Einwilligung zur Verarbeitung für festgelegte Zwecke (z. B. Fotoshooting) gegeben. Eine erteilte Einwilligung kann jederzeit mit Wirkung für die Zukunft widerrufen werden. Dies gilt auch für den Widerruf von Einwilligungserklärungen, die vor der Geltung der DSGVO, also vor dem 25. Mai 2018, uns gegenüber erteilt worden sind.
        </Typography>
        <Typography variant="body1" paragraph>
          <b>Kategorien von Empfängern der personenbezogenen Daten</b>
          <br />
          Innerhalb des Unternehmens sind die Stellen zugriffsberechtigt, die diese insbesondere zur Erfüllung unserer vertraglichen und gesetzlichen Pflichten benötigen. COUNT+CARE GMBH &amp; CO. KG lässt außerdem einzelne der vorgenannten Prozesse und Serviceleistungen durch sorgfältig ausgewählte und datenschutzkonform beauftragte Dienstleister ausführen, die ihren Sitz innerhalb der EU haben. Dies ist beim Fotoshooting vorliegend eine Marketing-Agentur.
          <br />
          Im Hinblick auf die Datenweitergabe an weitere Empfänger dürfen wir Informationen über Sie nur weitergeben, wenn gesetzliche Bestimmungen dies erfordern, Sie eingewilligt haben oder wir zur Weitergabe befugt sind.
        </Typography>
        <Typography variant="body1" paragraph>
          <b>Absicht, die personenbezogenen Daten an ein Drittland oder eine internationale Organisation zu übermitteln</b>
          <br />
          Die Fotos werden auch auf Diensten hochgeladen bzw. sind auf Webseiten auffindbar, die ihren Sitz bspw. in den USA haben. Einige dieser Drittstaaten gelten datenschutzrechtlich als unsicher. Dies kann dazu führen, dass Daten für uns nicht bekannte oder verhinderbare Zwecke genutzt werden.
        </Typography>
        <Typography variant="body1" paragraph>
          <b>Dauer, für die die personenbezogenen Daten gespeichert werden</b>
          <br />
          Die Kriterien zur Festlegung der Dauer der Speicherung bemessen sich nach den Zwecken der Verarbeitung.
          Die personenbezogenen Daten (insbesondere Fotoaufnahmen, Zugangsdaten) werden nach Ablauf von sieben Kalendertagen automatisiert gelöscht, es sei denn, die Betroffenen löschen diese vorab manuell.
        </Typography>
        <Typography variant="body1" paragraph>
          <b>Datenschutzrechte</b>
          <br />
          Jede/r Betroffene hat das Recht auf Auskunft nach Artikel 15 DSGVO, das Recht auf Berichtigung nach Artikel 16 DSGVO, das Recht auf Löschung nach Artikel 17 DSGVO, das Recht auf Einschränkung der Verarbeitung nach Artikel 18 DSGVO, das Recht auf Widerspruch aus Artikel 21 DSGVO sowie das Recht auf Datenübertragbarkeit aus Artikel 20 DSGVO. Beim Auskunftsrecht und beim Löschungsrecht gelten die Einschränkungen nach §§ 34 und 35 BDSG. Darüber hinaus besteht ein Beschwerderecht bei einer zuständigen Datenschutzaufsichtsbehörde (Artikel 77 DSGVO i.V.m. § 19 BDSG).
          <br />
          Eine erteilte Einwilligung in die Verarbeitung personenbezogener Daten können Sie jederzeit mit Wirkung für die Zukunft uns gegenüber widerrufen. Im Falle eines Widerrufs bleibt die Rechtmäßigkeit der Verarbeitung bis zu diesem Zeitpunkt unberührt. Dies gilt auch für den Widerruf von Einwilligungserklärungen, die vor der Geltung der Datenschutzgrundverordnung, also vor dem 25. Mai 2018, uns gegenüber erteilt worden sind.
        </Typography>
        <Typography variant="body1" paragraph>
          <b>Verpflichtung zur Bereitstellung und mögliche Folgen einer Nichtbereitstellung von Daten</b>
          <br />
          Die Teilnahme an den Fotoshootings ist freiwillig. Die Folge der Nichtbereitstellung der Daten ist, dass Sie nicht am Fotoshooting teilnehmen können.
        </Typography>
        <Typography variant="body1" paragraph>
          <b>Bestehen einer automatisierten Entscheidungsfindung einschließlich Profiling</b>
          <br />
          Eine automatisierte Entscheidungsfindung gemäß Artikel 22 DSGVO erfolgt nicht.
        </Typography>
      </Box>
    </Box>
  );
}
