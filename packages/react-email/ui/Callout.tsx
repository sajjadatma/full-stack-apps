import { Section, Text } from "@react-email/components"

type CalloutProps = React.PropsWithChildren & { dir?: "ltr" | "rtl" }

export const Callout = ({ children, dir = "ltr" }: CalloutProps) => (
  <Section
    style={{
      ...calloutStyle,
      borderLeft: dir === "ltr" ? "3px solid #00897b" : undefined,
      borderRight: dir === "rtl" ? "3px solid #00897b" : undefined,
      textAlign: dir === "rtl" ? "right" : "left",
    }}
  >
    {children}
  </Section>
)

type DetailProps = { label: string; value: string; dir?: "ltr" | "rtl" }

export const Detail = ({ label, value, dir = "ltr" }: DetailProps) => (
  <Text
    style={{
      ...detailStyle,
      direction: dir,
      textAlign: dir === "rtl" ? "right" : "left",
    }}
  >
    <span style={labelStyle}>{label}</span>
    <br />
    <span style={valueStyle}>{value}</span>
  </Text>
)

const calloutStyle = {
  backgroundColor: "#f2f8f7",
  margin: "24px 0 28px",
  padding: "6px 18px",
}

const detailStyle = {
  margin: "12px 0",
}

const labelStyle = {
  color: "#64748b",
  fontSize: "11px",
  fontWeight: "700",
  letterSpacing: "1px",
  lineHeight: "16px",
  textTransform: "uppercase" as const,
}

const valueStyle = {
  color: "#1e293b",
  fontFamily: 'Consolas, "Courier New", monospace',
  fontSize: "14px",
  fontWeight: "700",
  lineHeight: "22px",
  wordBreak: "break-all" as const,
}
