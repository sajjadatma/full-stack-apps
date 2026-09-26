import { Text } from "@react-email/components"
import { Callout, Detail } from "../ui/Callout"
import { Heading } from "../ui/Heading"
import { Layout } from "../ui/Layout"

type TestEmailProps = {
  project_name: string
  email: string
}

export default function TestEmailFa({
  project_name = "{{ project_name }}",
  email = "{{ email }}",
}: TestEmailProps) {
  return (
    <Layout
      dir="rtl"
      title={`${project_name} - ایمیل آزمایشی`}
      preview={`ارسال ایمیل ${project_name} به‌درستی کار می‌کند`}
      project_name={project_name}
      footerText={`© ${new Date().getFullYear()} ${project_name}. تمامی حقوق محفوظ است.`}
    >
      <Heading>ایمیل آزمایشی</Heading>
      <Text style={bodyTextStyle}>سلام،</Text>
      <Text style={bodyTextStyle}>
        این یک ایمیل آزمایشی از {project_name} است. اگر این پیام را می‌خوانید،
        ارسال ایمیل به‌درستی پیکربندی شده است.
      </Text>
      <Callout dir="rtl">
        <Detail label="ارسال‌شده به" value={email} dir="rtl" />
      </Callout>
      <Text style={supportingTextStyle}>
        اگر منتظر دریافت این ایمیل نبودید، می‌توانید آن را نادیده بگیرید.
      </Text>
    </Layout>
  )
}

const bodyTextStyle = {
  color: "#334155",
  fontSize: "15px",
  lineHeight: "26px",
  margin: "0 0 18px",
}

const supportingTextStyle = {
  color: "#64748b",
  fontSize: "14px",
  lineHeight: "23px",
  margin: "0 0 16px",
}
