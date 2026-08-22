import { Redirect } from "expo-router";

export default function CompleteProfile() {
  return <Redirect href={"/profile-completion" as any} />;
}

