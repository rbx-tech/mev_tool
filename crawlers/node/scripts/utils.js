import { GoogleSpreadsheet } from 'google-spreadsheet';
import {JWT} from 'google-auth-library';
import cred from '../../../resources/google_cred.json' with {type: "json"};


export async function initDoc() {
  const auth = new JWT({
    email: cred.client_email,
    key: cred.private_key,
    scopes: ["https://www.googleapis.com/auth/spreadsheets"]
  });
  const doc = new GoogleSpreadsheet('1syhj3G3b19HSaG11TbUlhoTqvyKhkxgPKj1Jd3nylI4', auth);
  await doc.loadInfo();
  return doc;
}