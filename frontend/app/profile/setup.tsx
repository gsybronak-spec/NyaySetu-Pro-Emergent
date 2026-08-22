import { Redirect } from "expo-router";
import { useAuth } from "@/src/context/AuthContext";

export default function ProfileSetup() {
  const { user } = useAuth();
  const isComplete = user?.profile_completed ?? user?.is_profile_complete ?? false;
  return <Redirect href={(isComplete ? "/profile/edit" : "/profile-completion") as any} />;
}

