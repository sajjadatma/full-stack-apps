import { Text } from "@react-email/components"
import { LinkButton } from "../ui/Button"
import { Heading } from "../ui/Heading"
import { Layout } from "../ui/Layout"
import { Link } from "../ui/Link"

type ResetPasswordProps = {
  project_name: string
  username: string
  link: string
  valid_hours: string
}

export default function ResetPasswordFa({
  project_name = "{{ project_name }}",
  username = "{{ username }}",
  link = "{{ link }}",
  valid_hours = "{{ valid_hours }}",
}: ResetPasswordProps) {
  return (
    <Layout
      dir="rtl"
      title={`${project_name} - بازیابی رمز عبور`}
      preview={`بازنشانی رمز عبور ${project_name} شما`}
      project_name={project_name}
      footerText={`© ${new Date().getFullYear()} ${project_name}. تمامی حقوق محفوظ است.`}
    >
      <Heading>رمز عبور خود را بازنشانی کنید</Heading>
      <Text style={bodyTextStyle}>سلام {username}،</Text>
      <Text style={bodyTextStyle}>
        درخواستی برای بازنشانی رمز عبور حساب کاربری {project_name} شما دریافت
        کردیم. با کلیک روی دکمه زیر رمز عبور جدیدی انتخاب کنید:
      </Text>
      <LinkButton href={link}>بازنشانی رمز عبور</LinkButton>
      <Text style={supportingTextStyle}>
        یا این پیوند را در مرورگر خود کپی و جای‌گذاری کنید:
        <br />
        <Link href={link}>{link}</Link>
      </Text>
      <Text style={supportingTextStyle}>
        این پیوند تا {valid_hours} ساعت دیگر منقضی می‌شود.
      </Text>
      <Text style={supportingTextStyle}>
        اگر درخواست بازیابی رمز عبور نداده‌اید، می‌توانید این ایمیل را نادیده
        بگیرید.
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
