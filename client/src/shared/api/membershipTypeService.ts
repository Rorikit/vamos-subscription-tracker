import { api } from "./client";
import { MembershipType } from "../types/domain";

export const membershipTypeService = {
  list: () => api<MembershipType[]>("/membership-types"),
  create: (payload: Partial<MembershipType>) =>
    api<MembershipType>("/membership-types", { method: "POST", body: JSON.stringify(payload) }),
  update: (id: number, payload: Partial<MembershipType>) =>
    api<MembershipType>(`/membership-types/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
};

