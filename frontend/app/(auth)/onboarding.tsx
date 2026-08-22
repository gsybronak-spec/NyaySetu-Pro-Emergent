import { Redirect } from "expo-router";

export default function Onboarding() {
  return <Redirect href={"/profile-completion" as any} />;
}


