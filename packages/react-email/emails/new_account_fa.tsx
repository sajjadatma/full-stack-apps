import { Text } from "@react-email/components"
import { LinkButton } from "../ui/Button"
import { Callout, Detail } from "../ui/Callout"
import { Heading } from "../ui/Heading"
import { Layout } from "../ui/Layout"
import { Link } from "../ui/Link"

type NewAccountProps = {
  project_name: string
  username: string
  password: string
  link: string
}

export default function NewAccountFa({
  project_name = "{{ project_name }}",
  username = "{{ username }}",
  password = "{{ password }}",
  link = "{{ link }}",
}: NewAccountProps) {
  return (
    <Layout
      dir="rtl"
      title={`${project_name} - حساب کاربری جدید`}
      preview={`حساب کاربری ${project_name} شما آماده است`}
      project_name={project_name}
      footerText={`© ${new Date().getFullYear()} ${project_name}. تمامی حقوق محفوظ است.`}
    >
      <Heading>به {project_name} خوش آمدید!</Heading>
      <Text style={bodyTextStyle}>سلام،</Text>
      <Text style={bodyTextStyle}>
        حساب کاربری شما با موفقیت ایجاد شد و آماده استفاده است. این‌ها اطلاعات
        ورود شما هستند:
      </Text>
      <Callout dir="rtl">
        <Detail label="نام کاربری" value={username} dir="rtl" />
        <Detail label="رمز عبور" value={password} dir="rtl" />
      </Callout>
      <Text style={bodyTextStyle}>برای شروع، وارد داشبورد خود شوید:</Text>
      <LinkButton href={link}>رفتن به داشبورد</LinkButton>
      <Text style={supportingTextStyle}>
        یا این پیوند را در مرورگر خود کپی و جای‌گذاری کنید:
        <br />
        <Link href={link}>{link}</Link>
      </Text>
      <Text style={supportingTextStyle}>
        بنا به دلایل امنیتی، پس از اولین ورود رمز عبور خود را تغییر دهید.
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
